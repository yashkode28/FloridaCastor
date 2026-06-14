"""Fetch forecast data from API and persist to database."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from src.api.app import FL_CITIES, NWS_HEADERS, points_lookup
from src.features.feature_utils import (
    forecast_to_df,
    risk_signals,
    build_cost_based_risk_score,
    score_to_label,
    heat_index,
)
from src.persist import upsert_weather_hourly


def fetch_forecast_for_city(city: str) -> dict:
    """
    Fetch forecast data from NWS API for a given city.
    
    Args:
        city: City name (must be in FL_CITIES)
    
    Returns:
        Dictionary with 'city', 'lat', 'lon', and 'hours' (list of forecast periods)
    """
    if city not in FL_CITIES:
        raise ValueError(
            f"City '{city}' not found. Available cities: {list(FL_CITIES.keys())}"
        )
    
    lat, lon = FL_CITIES[city]
    
    # Get forecast URL
    points = points_lookup(lat, lon)
    hourly_url = points["properties"]["forecastHourly"]
    
    # Fetch hourly forecast
    response = requests.get(hourly_url, headers=NWS_HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    # Get next 24 hours
    periods = data["properties"]["periods"][:24]
    
    # Simplify to match API format
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
    
    return {
        "city": city,
        "lat": lat,
        "lon": lon,
        "hours": simplified,
    }


def process_and_persist(city: str) -> int:
    """
    Complete pipeline: Fetch → Process → Persist.
    
    Args:
        city: City name to process
    
    Returns:
        Number of rows upserted
    """
    print(f"Fetching forecast for {city}...")
    forecast_data = fetch_forecast_for_city(city)
    
    print(f"Processing {len(forecast_data['hours'])} forecast periods...")
    # Convert to DataFrame
    df = forecast_to_df(forecast_data["hours"])
    
    # Add risk scoring
    if 'heat_index' not in df.columns:
        df['heat_index'] = heat_index(df['tempF'], df['humidity'])
    df = risk_signals(df)
    df = build_cost_based_risk_score(df)
    df['risk_label'] = df['risk_score_0_100'].apply(score_to_label)
    
    # Add city column (required for database)
    df["city"] = city
    
    print(f"Upserting to database...")
    n = upsert_weather_hourly(df, city=city)
    
    print(f"✅ Successfully upserted {n} rows for {city}")
    return n


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch and persist weather forecasts")
    parser.add_argument(
        "city",
        nargs="?",
        default="Miami",
        help="City name (default: Miami)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all cities",
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Process all cities
        total = 0
        for city in sorted(FL_CITIES.keys()):
            try:
                n = process_and_persist(city)
                total += n
            except Exception as e:
                print(f"❌ Error processing {city}: {e}")
        print(f"\n✅ Total rows upserted: {total}")
    else:
        # Process single city
        process_and_persist(args.city)
