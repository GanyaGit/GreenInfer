"""
ecoquery/app.py
Flask backend for EcoQuery — per-query CO2 + water footprint API.

Endpoints:
  GET /footprint?location=<name>&year=<int>
  GET /provinces
  GET /countries
  GET /health
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

# ── GreenInfer imports ────────────────────────────────────────────────────────
try:
    from greeninfer.calculator import calculate_footprint
    from greeninfer.regions import CHINA_PROVINCES_BY_YEAR, CHINA_PROVINCES
    from greeninfer.countries import COUNTRIES  # Ember-based dict {name: {year: intensity}}
except ImportError:
    # Fallback stubs so the server starts even without full greeninfer install
    CHINA_PROVINCES_BY_YEAR = {}
    CHINA_PROVINCES = {}
    COUNTRIES = {}

    def calculate_footprint(location, year=None):
        return {"error": "greeninfer not installed"}

app = Flask(__name__)
CORS(app)

# ── Constants ─────────────────────────────────────────────────────────────────
ENERGY_PER_QUERY_KWH = 0.001   # Patterson et al. 2021
PUE                  = 1.4     # industry average
WUE_ONSITE           = 0.25    # L/kWh  (Ren et al. 2025)
WUE_OFFSITE          = 4.73    # L/kWh  (Ren et al. 2025)

SUPPORTED_PROVINCE_YEARS = sorted(CHINA_PROVINCES_BY_YEAR.keys())
DEFAULT_PROVINCE_YEAR    = max(SUPPORTED_PROVINCE_YEARS) if SUPPORTED_PROVINCE_YEARS else 2025

# ── Helper ────────────────────────────────────────────────────────────────────

def compute_water(energy_kwh: float) -> float:
    """Return water footprint in mL using Ren et al. 2025 WUE formula."""
    onsite  = (energy_kwh / PUE) * WUE_ONSITE  * 1000
    offsite = energy_kwh         * WUE_OFFSITE  * 1000
    return round(onsite + offsite, 4)


def get_province_intensity(province: str, year: int) -> float | None:
    """
    Look up carbon intensity (gCO2/kWh) for a Chinese province in the given year.
    Falls back to the nearest available year if exact year is missing.
    Returns None if province is unknown.
    """
    if not CHINA_PROVINCES_BY_YEAR:
        return None

    # Clamp to supported range
    available_years = sorted(CHINA_PROVINCES_BY_YEAR.keys())
    clamped_year = max(available_years[0], min(year, available_years[-1]))

    year_data = CHINA_PROVINCES_BY_YEAR.get(clamped_year)
    if year_data is None:
        return None

    return year_data.get(province)  # None if unknown province


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/footprint")
def footprint():
    """
    Query params:
      location  (required) — country name or Chinese province name
      year      (optional) — integer year; defaults to most recent available
                             for provinces (2025), or the Ember data year for countries
    """
    location = request.args.get("location", "").strip()
    if not location:
        return jsonify({"error": "Missing required query parameter: location"}), 400

    year_param = request.args.get("year")
    year = None
    if year_param is not None:
        try:
            year = int(year_param)
        except ValueError:
            return jsonify({"error": f"Invalid year: {year_param!r}"}), 400

    # ── Province path ──────────────────────────────────────────────────────────
    all_province_names = set()
    for y in CHINA_PROVINCES_BY_YEAR.values():
        all_province_names.update(y.keys())

    if location in all_province_names:
        resolved_year = year if year is not None else DEFAULT_PROVINCE_YEAR
        intensity = get_province_intensity(location, resolved_year)

        if intensity is None:
            return jsonify({
                "error": f"Province '{location}' not found for year {resolved_year}",
                "available_years": SUPPORTED_PROVINCE_YEARS,
            }), 404

        co2_g = round(ENERGY_PER_QUERY_KWH * intensity, 4)
        water_ml = compute_water(ENERGY_PER_QUERY_KWH)

        return jsonify({
            "location":   location,
            "type":       "province",
            "year":       resolved_year,
            "intensity":  intensity,
            "co2_g":      co2_g,
            "water_ml":   water_ml,
            "energy_kwh": ENERGY_PER_QUERY_KWH,
        })

    # ── Country path ───────────────────────────────────────────────────────────
    if location in COUNTRIES:
        country_data = COUNTRIES[location]  # {year: intensity_gco2_kwh}

        if year is not None and year in country_data:
            resolved_year = year
        else:
            resolved_year = max(country_data.keys())

        intensity = country_data[resolved_year]
        co2_g     = round(ENERGY_PER_QUERY_KWH * intensity, 4)
        water_ml  = compute_water(ENERGY_PER_QUERY_KWH)

        return jsonify({
            "location":   location,
            "type":       "country",
            "year":       resolved_year,
            "intensity":  intensity,
            "co2_g":      co2_g,
            "water_ml":   water_ml,
            "energy_kwh": ENERGY_PER_QUERY_KWH,
        })

    return jsonify({"error": f"Location not found: {location!r}"}), 404


@app.route("/provinces")
def provinces():
    """Return all provinces with intensities for all available years."""
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
            "year":      year,
            "provinces": [
                {"name": k, "intensity": v, "co2_g": round(ENERGY_PER_QUERY_KWH * v, 4)}
                for k, v in sorted(data.items(), key=lambda x: -x[1])
            ],
        })

    # All years
    return jsonify({
        "available_years": SUPPORTED_PROVINCE_YEARS,
        "data": {
            str(yr): [
                {"name": k, "intensity": v, "co2_g": round(ENERGY_PER_QUERY_KWH * v, 4)}
                for k, v in sorted(prov.items(), key=lambda x: -x[1])
            ]
            for yr, prov in CHINA_PROVINCES_BY_YEAR.items()
        },
    })


@app.route("/countries")
def countries():
    """Return all countries with most-recent-year intensities."""
    year_param = request.args.get("year")
    result = []
    for name, year_data in COUNTRIES.items():
        if year_param is not None:
            try:
                y = int(year_param)
            except ValueError:
                return jsonify({"error": f"Invalid year: {year_param!r}"}), 400
            intensity = year_data.get(y)
        else:
            y = max(year_data.keys())
            intensity = year_data[y]

        if intensity is not None:
            result.append({
                "name":      name,
                "year":      y,
                "intensity": intensity,
                "co2_g":     round(ENERGY_PER_QUERY_KWH * intensity, 4),
            })

    result.sort(key=lambda x: -x["intensity"])
    return jsonify({"countries": result})


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
