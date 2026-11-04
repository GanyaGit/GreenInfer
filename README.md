# GreenInfer

Python library for estimating the CO₂ and water footprint of AI inference queries, broken down by country and Chinese province.

## Installation

```bash
pip install -e .
```

## Usage

```python
import greeninfer

# Any country
result = greeninfer.estimate(country="Germany")
print(result)

# China with province-level intensity (defaults to 2025 data)
result = greeninfer.estimate(country="China", province="Shanghai")
print(result["co2_grams"])  # grams of CO2
print(result["water_ml"])   # millilitres of water

# Pick a specific year (2024 or 2025 for Chinese provinces)
result = greeninfer.estimate(country="China", province="Beijing", year=2024)

# Country not in the dataset -- supply a manual intensity factor (gCO2/kWh)
result = greeninfer.estimate(country="Myanmar", manual_factor=620)

# Wrap real inference to measure actual energy use
with greeninfer.track(country="China", province="Beijing") as t:
    output = model.generate(prompt)
print(t.co2_grams, t.water_ml, t.method)
```

## How it works

**CO₂**

```
intensity (gCO₂/kWh) = round( thermal_fraction × 820 )
CO₂ (g)              = intensity × energy_per_query_kWh
```

Provincial intensity is derived from NBS monthly generation data (thermal, hydro, nuclear, wind, solar) using the IPCC AR5 lifecycle factor for coal (820 gCO₂/kWh). Country intensity comes from the Ember Yearly Electricity Data.

**Water** (Ren et al. 2025, arXiv:2505.09598)

```
water (mL) = ( (E / PUE) × WUE_onsite + E × WUE_offsite ) × 1000
```

With PUE = 1.4, WUE_onsite = 0.25 L/kWh, WUE_offsite = 4.73 L/kWh, this gives about **4.91 mL per query**.

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| NBS Monthly Electricity by Province | 31 provinces, 2024-2025 | Province thermal fraction |
| Ember Yearly Electricity Data | 209 countries | Country grid intensity |
| IPCC AR5 (2014) | -- | Coal lifecycle factor: 820 gCO₂/kWh |
| Patterson et al. (2021) | -- | Energy per query: ~0.001 kWh |
| Ren et al. (2025) arXiv:2505.09598 | -- | WUE constants for water estimate |

## License

MIT
