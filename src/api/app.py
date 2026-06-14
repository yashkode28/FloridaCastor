from __future__ import annotations

import math
import os
from functools import lru_cache

import requests
from flask import Flask, jsonify, render_template, request
from sqlalchemy import text

from src.db import get_engine
from src.features.feature_utils import (
    build_cost_based_risk_score,
    forecast_to_df,
    heat_index,
    risk_signals,
    score_to_label,
)

app = Flask(__name__)

# Florida Cities
FL_CITIES: dict[str, tuple[float, float]] = {
    "Miami": (25.7617, -80.1918),
    "Orlando": (28.5383, -81.3792),
    "Tampa": (27.9506, -82.4572),
    "Jacksonville": (30.3322, -81.6557),
    "Tallahassee": (30.4383, -84.2807),
    "Fort Lauderdale": (26.1224, -80.1373),
    "Sarasota": (27.3364, -82.5307),
    "Naples": (26.1420, -81.7948),
    "Pensacola": (30.4213, -87.2169),
    "Key West": (24.5551, -81.7800),
}

# NWS asks for a User-Agent with contact info (email or website)
NWS_HEADERS = {
    "User-Agent": "FloridaWeatherAdvisor/1.0 (contact: yashkode@gmail.com)",
    "Accept": "application/geo+json",
}

_LABEL_NAMES = {0: "Good", 1: "Caution", 2: "No-go"}


def _get_json(url: str) -> dict:
    r = requests.get(url, headers=NWS_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=256)
def points_lookup(lat: float, lon: float) -> dict:
    # cache this because points responses don't change frequently
    return _get_json(f"https://api.weather.gov/points/{lat},{lon}")


def _safe(v):
    """Convert NaN to None and numpy scalars to Python natives for JSON serialization."""
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f):
            return None
        # numpy scalars (int64, float64, etc.) have .item() which returns a Python native
        if hasattr(v, 'item'):
            v = v.item()
        if isinstance(v, float):
            return round(v, 1)
        return v
    except (TypeError, ValueError):
        pass
    return v


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    """Process is up (does not check the database)."""
    return jsonify({"status": "ok"})


@app.get("/health/db")
def health_db():
    """Verify SQLAlchemy can connect to PostgreSQL using DATABASE_URL or DB_* env vars."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            one = conn.execute(text("SELECT 1")).scalar()
        return jsonify({"status": "ok", "database": "connected", "select_1": int(one)})
    except Exception as e:
        return jsonify({"status": "error", "database": str(e)}), 503


@app.get("/cities")
def cities():
    """List supported Florida cities for the UI dropdown."""
    return jsonify(sorted(FL_CITIES.keys()))


@app.get("/forecast")
def forecast():
    """Return the next 24 hours of hourly forecast for a city.

    Query params:
      - city: one of /cities
    """
    city = request.args.get("city", "").strip()
    if city not in FL_CITIES:
        return (
            jsonify({"error": "Unknown city", "valid_cities": sorted(FL_CITIES.keys())}),
            400,
        )

    lat, lon = FL_CITIES[city]

    try:
        points = points_lookup(lat, lon)
        hourly_url = points["properties"]["forecastHourly"]

        data = _get_json(hourly_url)
        periods = data["properties"]["periods"][:24]  # next 24 hours

        simplified = [
            {
                "startTime": p["startTime"],
                "tempF": p["temperature"],
                "windSpeed": p["windSpeed"],
                "windDirection": p.get("windDirection"),
                "shortForecast": p.get("shortForecast"),
                "precipChance": (p.get("probabilityOfPrecipitation") or {}).get("value"),
                "humidity": (p.get("relativeHumidity") or {}).get("value"),
            }
            for p in periods
        ]

        return jsonify({"city": city, "lat": lat, "lon": lon, "hours": simplified})
    except requests.HTTPError as e:
        return jsonify({"error": "NWS request failed", "details": str(e)}), 502
    except KeyError as e:
        return jsonify({"error": "Unexpected NWS response shape", "missing_key": str(e)}), 502


@app.get("/recommend")
def recommend():
    """Return weather data + risk recommendation for a city.

    Runs the full feature engineering pipeline on NWS forecast data and returns
    the risk label, score, current conditions, and 24-hour breakdown.

    Query params:
      - city: one of /cities
    """
    city = request.args.get("city", "").strip()
    if city not in FL_CITIES:
        return jsonify({"error": "Unknown city", "valid_cities": sorted(FL_CITIES.keys())}), 400

    lat, lon = FL_CITIES[city]

    try:
        points = points_lookup(lat, lon)
        hourly_url = points["properties"]["forecastHourly"]
        data = _get_json(hourly_url)
        periods = data["properties"]["periods"][:24]

        raw_hours = [
            {
                "startTime": p["startTime"],
                "tempF": p["temperature"],
                "windSpeed": p["windSpeed"],
                "windDirection": p.get("windDirection"),
                "shortForecast": p.get("shortForecast"),
                "precipChance": (p.get("probabilityOfPrecipitation") or {}).get("value"),
                "humidity": (p.get("relativeHumidity") or {}).get("value"),
            }
            for p in periods
        ]

        df = forecast_to_df(raw_hours)
        df["heat_index"] = heat_index(df["tempF"], df["humidity"])
        df = risk_signals(df)
        df = build_cost_based_risk_score(df)
        df["risk_label"] = df["risk_score_0_100"].apply(score_to_label)

        peak_score = _safe(float(df["risk_score_0_100"].max()))
        peak_label = score_to_label(peak_score) if peak_score is not None else 0

        first = df.iloc[0]
        raw0 = raw_hours[0]

        current = {
            "tempF": _safe(first["tempF"]),
            "humidity": _safe(first["humidity"]),
            "wind_mph": _safe(first["wind_mph"]),
            "windDirection": raw0.get("windDirection"),
            "shortForecast": raw0.get("shortForecast"),
            "precip_prob": int(first["precip_prob"]),
            "thunderstorm": int(first["thunderstorm"]),
            "rain": int(first["rain"]),
            "heat_index": _safe(first["heat_index"]),
        }

        hours_out = [
            {
                "startTime": raw_hours[i]["startTime"],
                "tempF": _safe(row["tempF"]),
                "wind_mph": _safe(row["wind_mph"]),
                "precip_prob": int(row["precip_prob"]),
                "humidity": _safe(row["humidity"]),
                "thunderstorm": int(row["thunderstorm"]),
                "rain": int(row["rain"]),
                "risk_score": _safe(row["risk_score_0_100"]),
                "risk_label": int(row["risk_label"]),
                "label_text": _LABEL_NAMES[int(row["risk_label"])],
            }
            for i, (_, row) in enumerate(df.iterrows())
        ]

        return jsonify({
            "city": city,
            "overall": {
                "label": peak_label,
                "label_text": _LABEL_NAMES[peak_label],
                "score": peak_score,
                "season": str(df["florida_season"].iloc[0]),
            },
            "current": current,
            "hours": hours_out,
        })

    except requests.HTTPError as e:
        return jsonify({"error": "NWS request failed", "details": str(e)}), 502
    except KeyError as e:
        return jsonify({"error": "Unexpected NWS response shape", "missing_key": str(e)}), 502


if __name__ == "__main__":
    # Run with: python -m src.api.app  (from project root; PYTHONPATH includes cwd)
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
