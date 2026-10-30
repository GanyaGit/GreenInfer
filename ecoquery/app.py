# ecoquery/app.py
# EcoQuery — Flask REST API wrapping GreenInfer
#
# Endpoints:
#   GET  /                          → health check
#   GET  /estimate?country=China&province=Shanghai
#   GET  /provinces                 → list all China provinces
#   GET  /countries                 → list available countries sample
#
# Run:
#   cd ecoquery
#   pip install flask flask-cors
#   python app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add parent directory so greeninfer can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import greeninfer
from greeninfer.regions import CHINA_PROVINCES

app = Flask(__name__)
CORS(app)  # allow React frontend to call this API


# ── Health check ──────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "version": greeninfer.__version__,
        "message": "EcoQuery API is running"
    })


# ── Main estimate endpoint ─────────────────────────────────────
@app.route("/estimate")
def estimate():
    country       = request.args.get("country", "China")
    province      = request.args.get("province", None)
    year          = int(request.args.get("year", 2022))
    manual_factor = request.args.get("manual_factor", None)

    if manual_factor is not None:
        manual_factor = float(manual_factor)

    result = greeninfer.estimate(
        country=country,
        province=province,
        year=year,
        manual_factor=manual_factor,
    )

    return jsonify(result)


# ── List China provinces ───────────────────────────────────────
@app.route("/provinces")
def provinces():
    data = [
        {
            "name":          name,
            "co2_intensity": intensity,
            "co2_per_query": round(intensity * 0.001, 4),
            "water_ml":      1.8,
        }
        for name, intensity in sorted(CHINA_PROVINCES.items(),
                                      key=lambda x: x[1], reverse=True)
    ]
    return jsonify({"provinces": data, "count": len(data)})


# ── Compare multiple provinces ─────────────────────────────────
@app.route("/compare")
def compare():
    """
    Compare CO2 intensity across all provinces.
    Returns sorted list from highest to lowest.
    """
    results = []
    for province, intensity in CHINA_PROVINCES.items():
        results.append({
            "province":      province,
            "co2_intensity": intensity,
            "co2_per_query": round(intensity * 0.001, 4),
            "water_ml":      1.8,
            "category":      _category(intensity),
        })

    results.sort(key=lambda x: x["co2_intensity"], reverse=True)
    return jsonify({"data": results})


def _category(intensity: float) -> str:
    if intensity >= 800:
        return "very_high"
    elif intensity >= 600:
        return "high"
    elif intensity >= 400:
        return "medium"
    elif intensity >= 200:
        return "low"
    else:
        return "very_low"


# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)