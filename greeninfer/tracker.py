# greeninfer/tracker.py
# Context manager for wrapping real AI inference calls
# Auto-detects NVIDIA GPU via pynvml; falls back to time-based CPU estimate
#
# Usage:
#   with greeninfer.track(country="China", province="Shanghai") as t:
#       output = model.generate(input)
#   print(t.co2_grams, t.water_ml, t.method)

import time
from .estimator import estimate, ENERGY_PER_QUERY_KWH, WUE_ML_PER_KWH

# CPU power estimate when no GPU is available
CPU_WATTS_ESTIMATE = 15.0  # watts (typical inference CPU core load)


class InferenceTracker:
    """
    Context manager that measures energy during inference and
    converts it to CO2 + water footprint.
    """

    def __init__(self, country: str, province: str | None = None,
                 year: int = 2022, manual_factor: float | None = None):
        self.country       = country
        self.province      = province
        self.year          = year
        self.manual_factor = manual_factor

        # Filled after __exit__
        self.co2_grams     = None
        self.water_ml      = None
        self.co2_intensity = None
        self.method        = None
        self.energy_kwh    = None
        self.duration_s    = None

        self._start_time   = None
        self._nvml_handle  = None
        self._use_gpu      = False

    def __enter__(self):
        self._start_time = time.perf_counter()
        self._try_init_gpu()
        return self

    def _try_init_gpu(self):
        """Try to initialise pynvml for GPU power reading."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._use_gpu = True
        except Exception:
            self._use_gpu = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self._start_time
        self.duration_s = elapsed

        # Measure energy
        if self._use_gpu:
            energy_kwh = self._gpu_energy_kwh(elapsed)
            meas_method = "gpu_measured"
        else:
            energy_kwh = self._cpu_energy_kwh(elapsed)
            meas_method = "cpu_estimated"

        self.energy_kwh = energy_kwh

        # Get CO2/water from estimator
        result = estimate(
            country=self.country,
            province=self.province,
            year=self.year,
            energy_kwh=energy_kwh,
            manual_factor=self.manual_factor,
        )

        self.co2_grams     = result["co2_grams"]
        self.water_ml      = result["water_ml"]
        self.co2_intensity = result.get("co2_intensity")
        # Combine grid method + measurement method
        self.method        = f"{meas_method}+{result['method']}"

        # Clean up pynvml
        if self._use_gpu:
            try:
                import pynvml
                pynvml.nvmlShutdown()
            except Exception:
                pass

        return False  # do not suppress exceptions

    def _gpu_energy_kwh(self, elapsed_s: float) -> float:
        """Read GPU power draw and compute energy consumed."""
        try:
            import pynvml
            power_mw = pynvml.nvmlDeviceGetPowerUsage(self._nvml_handle)
            power_w  = power_mw / 1000.0
        except Exception:
            power_w = 100.0  # fallback: 100W GPU estimate
        energy_wh  = power_w * (elapsed_s / 3600.0)
        return energy_wh / 1000.0  # → kWh

    def _cpu_energy_kwh(self, elapsed_s: float) -> float:
        """Estimate CPU energy from elapsed time and CPU_WATTS_ESTIMATE."""
        energy_wh = CPU_WATTS_ESTIMATE * (elapsed_s / 3600.0)
        return energy_wh / 1000.0  # → kWh

    def __repr__(self):
        if self.co2_grams is None:
            return "<InferenceTracker: not yet run>"
        return (
            f"<InferenceTracker "
            f"co2={self.co2_grams:.4f}g "
            f"water={self.water_ml:.2f}mL "
            f"energy={self.energy_kwh:.6f}kWh "
            f"method={self.method}>"
        )


def track(country: str, province: str | None = None,
          year: int = 2022, manual_factor: float | None = None) -> InferenceTracker:
    """
    Return an InferenceTracker context manager.

    Example
    -------
    with greeninfer.track(country="China", province="Shanghai") as t:
        output = model.generate(prompt)
    print(t.co2_grams)   # grams of CO2
    print(t.water_ml)    # millilitres of water
    print(t.method)      # e.g. "gpu_measured+province"
    """
    return InferenceTracker(
        country=country,
        province=province,
        year=year,
        manual_factor=manual_factor,
    )