# GreenInfer

A Python library for estimating the **CO₂ and water footprint** of AI inference queries, by country and Chinese province.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
import greeninfer

# Estimate for any country
result = greeninfer.estimate(country="Germany")
print(result)

# China with province-level intensity
result = greeninfer.estimate(country="China", province="Shanghai")
print(result["co2_grams"])   # grams of CO2
print(result["water_ml"])    # millilitres of water

# Country not in dataset — use manual factor
result = greeninfer.estimate(country="Myanmar", manual_factor=620)

# Wrap real inference and measure actual energy
with greeninfer.track(country="China", province="Beijing") as t:
    output = model.generate(prompt)
print(t.co2_grams, t.water_ml, t.method)
```

## Methodology

- **CO₂** = thermal_fraction × 820 gCO₂/kWh × energy_per_query_kWh
- **Water** = energy_per_query_kWh × 1800 mL/kWh
- Grid mix data: [Our World in Data](https://ourworldindata.org/electricity-mix) (bundled)
- China province intensities: CEADs (Liu et al., 2022)
- Emission factor: IEA (2023) — 820 gCO₂/kWh for thermal generation
- Energy per query: de Vries (2023) — ~0.001 kWh

## Data Sources

| Source | Coverage | Used for |
|--------|----------|----------|
| OWID electricity mix | 200+ countries | National thermal fraction |
| CEADs (Liu et al. 2022) | 31 China provinces | Province CO₂ intensity |
| IEA (2023) | Global | Thermal emission factor |
| de Vries (2023) | Global | Energy per AI query |

## License

MIT