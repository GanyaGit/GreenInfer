# greeninfer/estimator.py
# Core CO2 and water footprint estimation logic
#
# Methodology:
#   CO2 (grams) = thermal_fraction × 820 gCO2/kWh × energy_per_query_kWh
#   Water (mL)  = energy_per_query_kWh × 1800 mL/kWh (WUE industry avg)
#
# References:
#   - IEA (2023): 820 gCO2/kWh for thermal/coal generation
#   - de Vries (2023): ~0.001 kWh per medium-complexity AI query
#   - WUE industry average: 1.8 L/kWh = 1800 mL/kWh
#   - OWID electricity mix dataset (bundled): Our World in Data

import os
import pandas as pd

# Constants
THERMAL_EMISSION_FACTOR = 820     # gCO2/kWh (IEA 2023, coal/thermal)
ENERGY_PER_QUERY_KWH    = 0.001   # kWh per medium-complexity AI query
WUE_ML_PER_KWH          = 1800    # mL water per kWh (1.8 L/kWh)

# Path to bundled OWID dataset
_DATA_PATH = os.path.join(os.path.dirname(__file__), "data",
                          "electricity-generation-by-source.csv")

_owid_df = None  # lazy-loaded cache


def _load_owid():
    """Load and cache the OWID electricity mix dataset."""
    global _owid_df
    if _owid_df is None:
        _owid_df = pd.read_csv(_DATA_PATH)
    return _owid_df


def _get_thermal_fraction_owid(country: str, year: int = 2022) -> float | None:
    """
    Look up thermal fraction for a country from OWID dataset.
    Returns float (0–1) or None if country not found.

    Thermal sources = Coal + Gas + Oil
    Total = Coal + Gas + Oil + Hydro + Nuclear + Wind + Solar +
            Bioenergy + Other renewables
    """
    df = _load_owid()

    # Try exact match first, then case-insensitive
    mask = (df["Entity"].str.lower() == country.lower()) & (df["Year"] == year)
    row = df[mask]

    # If exact year not found, use most recent available year
    if row.empty:
        mask_country = df["Entity"].str.lower() == country.lower()
        country_data = df[mask_country]
        if country_data.empty:
            return None
        row = country_data.sort_values("Year").iloc[[-1]]

    row = row.iloc[0]

    thermal_cols = ["Coal", "Gas", "Oil"]
    all_cols     = ["Coal", "Gas", "Oil", "Hydropower", "Nuclear",
                    "Wind", "Solar", "Bioenergy", "Other renewables"]

    # Sum only columns that exist and are not NaN
    thermal = sum(row.get(c, 0) or 0 for c in thermal_cols if c in row.index)
    total   = sum(row.get(c, 0) or 0 for c in all_cols   if c in row.index)

    if total == 0:
        return None

    return thermal / total


def estimate(
    country: str,
    province: str | None = None,
    year: int = 2022,
    energy_kwh: float = ENERGY_PER_QUERY_KWH,
    manual_factor: float | None = None,
) -> dict:
    """
    Estimate CO2 and water footprint for one AI inference query.

    Parameters
    ----------
    country       : Country name (matched against OWID dataset)
    province      : China province name (uses province-level intensity if given)
    year          : Grid mix year to use (default 2022)
    energy_kwh    : Energy consumed per query in kWh (default 0.001)
    manual_factor : Override CO2 intensity in gCO2/kWh (for unlisted countries)

    Returns
    -------
    dict with keys:
        co2_grams     : float
        water_ml      : float
        co2_intensity : float  (gCO2/kWh used)
        method        : str    ("province" | "owid" | "manual" | "unknown")
        country       : str
        province      : str or None
    """
    from .regions import CHINA_PROVINCES, CHINA_NATIONAL_AVG

    method       = "unknown"
    co2_intensity = None  # gCO2/kWh

    # 1. Manual override takes top priority
    if manual_factor is not None:
        co2_intensity = manual_factor
        method        = "manual"

    # 2. China province-level lookup
    elif country.lower() == "china" and province is not None:
        prov_key = province.strip().title()
        if prov_key in CHINA_PROVINCES:
            co2_intensity = CHINA_PROVINCES[prov_key]
            method        = "province"
        else:
            # Unknown province → fall back to national average
            co2_intensity = CHINA_NATIONAL_AVG
            method        = "china_national"

    # 3. OWID dataset lookup
    else:
        thermal_frac = _get_thermal_fraction_owid(country, year)
        if thermal_frac is not None:
            co2_intensity = thermal_frac * THERMAL_EMISSION_FACTOR
            method        = "owid"
        elif country.lower() == "china":
            # China fallback: national average
            co2_intensity = CHINA_NATIONAL_AVG
            method        = "china_national"

    # 4. Unknown country — return zeroes with warning
    if co2_intensity is None:
        return {
            "co2_grams":     0.0,
            "water_ml":      0.0,
            "co2_intensity": None,
            "method":        "unknown",
            "country":       country,
            "province":      province,
            "warning":       (
                f"Country '{country}' not found in dataset. "
                "Pass manual_factor=<gCO2/kWh> to override."
            ),
        }

    co2_grams = co2_intensity * energy_kwh
    water_ml  = energy_kwh * WUE_ML_PER_KWH

    return {
        "co2_grams":     round(co2_grams, 4),
        "water_ml":      round(water_ml,  4),
        "co2_intensity": round(co2_intensity, 2),
        "method":        method,
        "country":       country,
        "province":      province,
    }