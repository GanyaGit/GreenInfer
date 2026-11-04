"""
ecoquery/app.py
Flask backend for EcoQuery — per-query CO2 + water footprint API.

Endpoints:
  GET /footprint?location=<name>&year=<int>&type=province|country
  GET /provinces?year=<int>
  GET /countries?year=<int>
  GET /health
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from greeninfer.regions import CHINA_PROVINCES_BY_YEAR
    from greeninfer.estimator import (
        ENERGY_PER_QUERY_KWH,
        PUE,
        WUE_ONSITE,
        WUE_OFFSITE,
        _load_country_intensities,
        _load_latest_year_per_country,
        get_global_max_year,
    )
    _GREENINFER_OK = True
except ImportError as _e:
    print(f"[EcoQuery] WARNING: greeninfer import failed: {_e}")
    CHINA_PROVINCES_BY_YEAR = {}
    ENERGY_PER_QUERY_KWH = 0.001
    PUE = 1.4
    WUE_ONSITE = 0.25
    WUE_OFFSITE = 4.73
    def _load_latest_year_per_country():
        return {}
    def get_global_max_year():
        return 2023
    _GREENINFER_OK = False

app = Flask(__name__)
CORS(app)

SUPPORTED_PROVINCE_YEARS = sorted(CHINA_PROVINCES_BY_YEAR.keys())
DEFAULT_PROVINCE_YEAR    = max(SUPPORTED_PROVINCE_YEARS) if SUPPORTED_PROVINCE_YEARS else 2025
DEFAULT_COUNTRY_YEAR     = 2024  # fallback only; actual default is per-country latest year


def compute_water(energy_kwh: float) -> float:
    onsite  = (energy_kwh / PUE) * WUE_ONSITE  * 1000
    offsite = energy_kwh         * WUE_OFFSITE  * 1000
    return round(onsite + offsite, 4)


def get_all_province_names():
    names = set()
    for y in CHINA_PROVINCES_BY_YEAR.values():
        names.update(y.keys())
    return names


def get_province_intensity(province: str, year: int):
    if not CHINA_PROVINCES_BY_YEAR:
        return None, None
    available_years = sorted(CHINA_PROVINCES_BY_YEAR.keys())
    clamped_year = max(available_years[0], min(year, available_years[-1]))
    year_data = CHINA_PROVINCES_BY_YEAR.get(clamped_year)
    if year_data is None:
        return None, None
    match = next((k for k in year_data if k.lower() == province.lower()), None)
    return (year_data[match], clamped_year) if match else (None, None)


# Routes

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "greeninfer": _GREENINFER_OK,
        "province_years": SUPPORTED_PROVINCE_YEARS,
    })


@app.route("/footprint")
def footprint():
    location  = request.args.get("location", "").strip()
    loc_type  = request.args.get("type", "").strip().lower()  # "province" or "country"

    if not location:
        return jsonify({"error": "Missing required query parameter: location"}), 400

    year_param = request.args.get("year")
    year = None
    if year_param is not None:
        try:
            year = int(year_param)
        except ValueError:
            return jsonify({"error": f"Invalid year: {year_param!r}"}), 400

    # Province path — only if type is "province" or unspecified
    if loc_type != "country":
        all_province_names = get_all_province_names()
        match_prov = next((p for p in all_province_names if p.lower() == location.lower()), None)

        if match_prov:
            resolved_year = year if year is not None else DEFAULT_PROVINCE_YEAR
            intensity, actual_year = get_province_intensity(match_prov, resolved_year)

            if intensity is None:
                return jsonify({
                    "error": f"Province '{location}' not found for year {resolved_year}",
                    "available_years": SUPPORTED_PROVINCE_YEARS,
                }), 404

            return jsonify({
                "location":   match_prov,
                "type":       "province",
                "year":       actual_year,
                "intensity":  intensity,
                "co2_g":      round(ENERGY_PER_QUERY_KWH * intensity, 4),
                "water_ml":   compute_water(ENERGY_PER_QUERY_KWH),
                "energy_kwh": ENERGY_PER_QUERY_KWH,
            })

        # If type was explicitly "province" and nothing matched
        if loc_type == "province":
            return jsonify({"error": f"Province not found: {location!r}"}), 404

    # Country path
    if not _GREENINFER_OK:
        return jsonify({"error": f"Location not found: {location!r}"}), 404

    try:
        # If no year given, use that country's own latest available year
        if year is None:
            latest_per_country = _load_latest_year_per_country()
            # We don't know the exact key yet, so use global max as first attempt
            ember_year = get_global_max_year()
        else:
            ember_year = year
        intensities = _load_country_intensities(ember_year)
        match_key = next(
            (k for k in intensities if k.lower() == location.lower()), None
        )
        # If not found at global max year and no explicit year given, fall back to country's own latest year
        if match_key is None and year is None:
            latest_per_country = _load_latest_year_per_country()
            country_match = next(
                (k for k in latest_per_country if k.lower() == location.lower()), None
            )
            if country_match:
                ember_year = latest_per_country[country_match]
                intensities = _load_country_intensities(ember_year)
                match_key = next(
                    (k for k in intensities if k.lower() == location.lower()), None
                )
        if match_key:
            intensity = intensities[match_key]
            latest_per_country = _load_latest_year_per_country()
            return jsonify({
                "location":    match_key,
                "type":        "country",
                "year":        ember_year,
                "latest_year": latest_per_country.get(match_key, ember_year),
                "intensity":   round(float(intensity), 1),
                "co2_g":       round(ENERGY_PER_QUERY_KWH * float(intensity), 4),
                "water_ml":    compute_water(ENERGY_PER_QUERY_KWH),
                "energy_kwh":  ENERGY_PER_QUERY_KWH,
            })
    except Exception as exc:
        return jsonify({"error": f"Country lookup failed: {exc}"}), 500

    return jsonify({"error": f"Location not found: {location!r}"}), 404


@app.route("/provinces")
def provinces():
    year_param = request.args.get("year")

    if year_param is not None:
        try:
            year = int(year_param)
        except ValueError:
            return jsonify({"error": f"Invalid year: {year_param!r}"}), 400

        data = CHINA_PROVINCES_BY_YEAR.get(year)
        if data is None:
            return jsonify({
                "error": f"No provincial data for year {year}",
                "available_years": SUPPORTED_PROVINCE_YEARS,
            }), 404

        return jsonify({
            "year": year,
            "provinces": [
                {
                    "name":      k,
                    "intensity": v,
                    "co2_g":     round(ENERGY_PER_QUERY_KWH * v, 4),
                    "water_ml":  compute_water(ENERGY_PER_QUERY_KWH),
                }
                for k, v in sorted(data.items(), key=lambda x: -x[1])
            ],
        })

    return jsonify({
        "available_years": SUPPORTED_PROVINCE_YEARS,
        "data": {
            str(yr): [
                {
                    "name":      k,
                    "intensity": v,
                    "co2_g":     round(ENERGY_PER_QUERY_KWH * v, 4),
                    "water_ml":  compute_water(ENERGY_PER_QUERY_KWH),
                }
                for k, v in sorted(prov.items(), key=lambda x: -x[1])
            ]
            for yr, prov in CHINA_PROVINCES_BY_YEAR.items()
        },
    })


@app.route("/countries/max_year")
def countries_max_year():
    """Return the global maximum year available in the Ember dataset."""
    if not _GREENINFER_OK:
        return jsonify({"max_year": DEFAULT_COUNTRY_YEAR})
    try:
        return jsonify({"max_year": get_global_max_year()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/countries")
def countries():
    if not _GREENINFER_OK:
        return jsonify({"countries": [], "max_year": DEFAULT_COUNTRY_YEAR})

    year_param = request.args.get("year")

    try:
        latest_per_country = _load_latest_year_per_country()
        global_max = get_global_max_year()
    except Exception as exc:
        return jsonify({"error": f"Failed to load year metadata: {exc}"}), 500

    # If no year specified, use global max year (latest data available for any country)
    try:
        ember_year = int(year_param) if year_param else global_max
    except ValueError:
        return jsonify({"error": f"Invalid year: {year_param!r}"}), 400

    try:
        intensities = _load_country_intensities(ember_year)
    except Exception as exc:
        return jsonify({"error": f"Failed to load country data: {exc}"}), 500

    result = [
        {
            "name":        name,
            "year":        ember_year,
            "latest_year": latest_per_country.get(name, ember_year),
            "intensity":   round(float(val), 1),
            "co2_g":       round(ENERGY_PER_QUERY_KWH * float(val), 4),
            "water_ml":    compute_water(ENERGY_PER_QUERY_KWH),
        }
        for name, val in intensities.items()
        if val is not None
    ]
    result.sort(key=lambda x: -x["intensity"])
    return jsonify({"countries": result, "year": ember_year, "max_year": global_max})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
