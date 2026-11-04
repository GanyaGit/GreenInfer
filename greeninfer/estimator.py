# greeninfer/estimator.py
#
# CO2:   intensity × energy_per_query_kWh
# Water: Ren et al. (2025) WUE method
#           onsite  = (E / PUE) × WUE_ONSITE  × 1000  mL
#           offsite = E          × WUE_OFFSITE × 1000  mL
#
# Province intensity = round( thermal_annual / total_annual × 820 )
# Source: NBS Monthly electricity by province, 2024-2025
# Country intensity: Ember Yearly Electricity Data (209 countries)
#   Column used: "Emissions intensity (gCO2e/kWh)" where
#   "Electricity source" == "Total generation" and "Area type" == "Country or economy"

import os
import pandas as pd
from .regions import CHINA_PROVINCES_BY_YEAR

ENERGY_PER_QUERY_KWH = 0.001   # Patterson et al. (2021)
COAL_FACTOR          = 820     # gCO2/kWh -- IPCC AR5 (2014) coal lifecycle

PUE             = 1.4          # Power Usage Effectiveness, industry average
WUE_ONSITE      = 0.25         # L/kWh on-site (Ren et al. 2025)
WUE_OFFSITE     = 4.73         # L/kWh off-site (Ren et al. 2025)

WUE_ML_PER_KWH  = round(((1 / PUE) * WUE_ONSITE + WUE_OFFSITE) * 1000, 4)

_DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
_EMBER_CSV = os.path.join(_DATA_DIR, "release_generation_yearly_global.csv")

_country_cache: dict[int, dict[str, float]] = {}
_latest_year_cache: dict[str, int] | None = None
_global_max_year: int | None = None


def _load_latest_year_per_country() -> dict[str, int]:
    """Return {country_name: latest_year_with_data} for all countries."""
    global _latest_year_cache
    if _latest_year_cache is not None:
        return _latest_year_cache
    df = pd.read_csv(_EMBER_CSV)
    mask = (
        (df["Area type"] == "Country or economy") &
        (df["Electricity source"] == "Total generation")
    )
    sub = df[mask][["Area", "Year", "Emissions intensity (gCO2e/kWh)"]].dropna()
    # For each country, find the latest year that has a non-negative intensity value
    sub = sub[sub["Emissions intensity (gCO2e/kWh)"] >= 0]
    _latest_year_cache = sub.groupby("Area")["Year"].max().to_dict()
    return _latest_year_cache


def get_global_max_year() -> int:
    """Return the latest year available in the Ember dataset for any country."""
    global _global_max_year
    if _global_max_year is not None:
        return _global_max_year
    latest = _load_latest_year_per_country()
    _global_max_year = max(latest.values()) if latest else 2023
    return _global_max_year


def _load_country_intensities(year: int) -> dict[str, float]:
    """
    Load pre-computed grid intensity (gCO2e/kWh) for all countries from the
    Ember Yearly Electricity Data CSV for the given year.
    Returns {country_name: intensity_gco2_kwh}.
    """
    if year in _country_cache:
        return _country_cache[year]

    df = pd.read_csv(_EMBER_CSV)

    # Filter to countries only, the given year, and the "Total generation" row
    mask = (
        (df["Area type"] == "Country or economy") &
        (df["Year"] == year) &
        (df["Electricity source"] == "Total generation")
    )
    sub = df[mask][["Area", "Emissions intensity (gCO2e/kWh)"]].dropna()

    result = {
        row["Area"]: round(float(row["Emissions intensity (gCO2e/kWh)"]), 1)
        for _, row in sub.iterrows()
        if row["Emissions intensity (gCO2e/kWh)"] >= 0
    }

    _country_cache[year] = result
    return result


def _water_ml(energy_kwh: float) -> float:
    onsite  = (energy_kwh / PUE) * WUE_ONSITE  * 1000
    offsite =  energy_kwh        * WUE_OFFSITE  * 1000
    return round(onsite + offsite, 4)


def estimate(
    country:       str,
    province:      str | None   = None,
    year:          int          = 2025,
    energy_kwh:    float | None = None,
    manual_factor: float | None = None,
) -> dict:
    """
    Estimate CO2 (grams) and water (mL) for one AI inference query.

    Parameters
    ----------
    country       : Country name matching the Ember dataset (e.g. "Germany").
    province      : Chinese province name; used only when country="China".
    year          : Data year. For provinces: 2024 or 2025. For countries: any
                    year available in the Ember CSV.
    energy_kwh    : Measured energy in kWh. Defaults to ENERGY_PER_QUERY_KWH.
    manual_factor : Override grid intensity (gCO2/kWh), skips all data lookups.

    Returns
    -------
    dict
        co2_grams     : float
        water_ml      : float
        co2_intensity : float | None
        method        : "province" | "country" | "manual" | "unknown"
    """
    e = energy_kwh if energy_kwh is not None else ENERGY_PER_QUERY_KWH

    if manual_factor is not None:
        intensity = float(manual_factor)
        return {
            "co2_grams":     round(intensity * e, 6),
            "water_ml":      _water_ml(e),
            "co2_intensity": intensity,
            "method":        "manual",
        }

    if country.lower() == "china" and province:
        avail = sorted(CHINA_PROVINCES_BY_YEAR.keys())
        yr    = max(avail[0], min(avail[-1], year))
        prov_map = CHINA_PROVINCES_BY_YEAR[yr]

        match = next(
            (k for k in prov_map if k.lower() == province.lower()), None
        )
        if match:
            intensity = float(prov_map[match])
            return {
                "co2_grams":     round(intensity * e, 6),
                "water_ml":      _water_ml(e),
                "co2_intensity": intensity,
                "method":        "province",
            }

    try:
        intensities = _load_country_intensities(year)
        match_key = next(
            (k for k in intensities if k.lower() == country.lower()), None
        )
        if match_key:
            intensity = float(intensities[match_key])
            return {
                "co2_grams":     round(intensity * e, 6),
                "water_ml":      _water_ml(e),
                "co2_intensity": intensity,
                "method":        "country",
            }
    except Exception:
        pass

    return {
        "co2_grams":     None,
        "water_ml":      _water_ml(e),
        "co2_intensity": None,
        "method":        "unknown",
    }
