"""Test script for persisting data to database."""
from __future__ import annotations

import pandas as pd
from src.persist import upsert_weather_hourly, ensure_location_columns
from src.features.feature_utils import forecast_to_df, risk_signals, build_cost_based_risk_score, score_to_label, heat_index

# Example: Create a test DataFrame (simulating your pipeline)
# In your actual notebook, you'd use df_cleaned from your feature engineering

# Sample data structure matching your pipeline output
sample_data = {
    "startTime": ["2026-01-27T16:00:00-05:00", "2026-01-27T17:00:00-05:00"],
    "tempF": [67, 66],
    "windDirection": ["N", "N"],
    "precipChance": [0, 0],
    "humidity": [59, 61],
    "windSpeed": ["15 mph", "15 mph"],
    "shortForecast": ["Sunny", "Sunny"],
}

# Convert to DataFrame and apply feature engineering
df = forecast_to_df(sample_data)

# Add risk scoring (if not already done)
if 'heat_index' not in df.columns:
    df['heat_index'] = heat_index(df['tempF'], df['humidity'])
df = risk_signals(df)
df = build_cost_based_risk_score(df)
df['risk_label'] = df['risk_score_0_100'].apply(score_to_label)

# Add city column (REQUIRED)
city_name = "Miami"
df["city"] = city_name

print("=" * 80)
print("PREPARING DATA FOR DATABASE")
print("=" * 80)
print(f"\nDataFrame shape: {df.shape}")
print(f"\nColumns: {list(df.columns)}")
print(f"\nCity column present: {'city' in df.columns}")
print(f"\nSample data:")
print(df[['city', 'startTime', 'tempF', 'wind_mph', 'risk_score_0_100', 'risk_label']].head())

# Upsert to database
print("\n" + "=" * 80)
print("UPSERTING TO DATABASE")
print("=" * 80)
try:
    n = upsert_weather_hourly(df, city=city_name)
    print(f"\n✅ Upserted {n} rows successfully!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    raise

# After your feature engineering pipeline
df["city"] = "Miami"  # or whatever city you're processing

# Then upsert
from src.persist import upsert_weather_hourly
n = upsert_weather_hourly(df)
print("Upserted rows:", n)