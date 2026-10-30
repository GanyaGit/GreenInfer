# greeninfer/__init__.py
# GreenInfer — CO2 and water footprint estimator for AI inference
#
# Public API:
#   greeninfer.estimate(country, province, year, energy_kwh, manual_factor)
#   greeninfer.track(country, province, year, manual_factor)
#
# Examples:
#   import greeninfer
#   result = greeninfer.estimate(country="China", province="Shanghai")
#   result = greeninfer.estimate(country="Germany")
#   result = greeninfer.estimate(country="Sri Lanka", manual_factor=650)
#
#   with greeninfer.track(country="China", province="Beijing") as t:
#       output = model.generate(prompt)
#   print(t.co2_grams, t.water_ml)

__version__ = "0.1.0"
__author__  = "Gayani Upeksha"
__email__   = "gayaniupeksha2906@gmail.com"

from .estimator import estimate
from .tracker   import track

__all__ = ["estimate", "track", "__version__"]