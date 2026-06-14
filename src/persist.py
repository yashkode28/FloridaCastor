"""Persist weather forecast data to the database."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.db import get_engine

# Import FL_CITIES for coordinate lookup
try:
    from src.api.app import FL_CITIES
except ImportError:
    # Fallback if not available
    FL_CITIES = {
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


def ensure_location_columns(df: pd.DataFrame, city: str | None = None) -> pd.DataFrame:
    """
    Ensure DataFrame has city, latitude, and longitude columns.
    
    If city column doesn't exist, adds it from the city parameter.
    If latitude/longitude don't exist, looks them up from FL_CITIES.
    
    Args:
        df: DataFrame to modify
        city: City name (required if 'city' column doesn't exist)
    
    Returns:
        DataFrame with city, latitude, longitude columns
    """
    df = df.copy()
    
    # Add city column if missing
    if 'city' not in df.columns:
        if city is None:
            raise ValueError(
                "DataFrame missing 'city' column and no city parameter provided. "
                "Either add 'city' column to DataFrame or pass city='Miami' etc."
            )
        df['city'] = city
    
    # Add latitude/longitude if missing
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        # Get coordinates for the city (use first row's city if all same)
        city_name = df['city'].iloc[0] if len(df) > 0 else city
        
        if city_name not in FL_CITIES:
            raise ValueError(
                f"City '{city_name}' not found in FL_CITIES. "
                f"Available cities: {list(FL_CITIES.keys())}"
            )
        
        lat, lon = FL_CITIES[city_name]
        
        if 'latitude' not in df.columns:
            df['latitude'] = lat
        if 'longitude' not in df.columns:
            df['longitude'] = lon
    
    return df


def upsert_weather_hourly(
    df: pd.DataFrame,
    city: str | None = None,
    table_name: str = "forecasts"
) -> int:
    """
    Upsert (insert or update) weather forecast data to the database.
    
    Uses PostgreSQL's ON CONFLICT to update existing rows based on (city, start_time).
    
    Args:
        df: DataFrame with weather forecast data and features
        city: City name (optional if 'city' column exists)
        table_name: Database table name (default: 'forecasts')
    
    Returns:
        Number of rows upserted
    """
    # Ensure required columns exist
    df = ensure_location_columns(df, city=city)
    
    # Column mapping: DataFrame column -> Database column
    column_mapping = {
        'city': 'city',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'startTime': 'start_time',
        'tempF': 'temp_f',
        'windDirection': 'wind_direction',
        'precipChance': 'precip_chance',
        'humidity': 'humidity',
        'wind_mph': 'wind_mph',
        'precip_prob': 'precip_prob',
        'hours': 'hours',
        'month': 'month',
        'month_sin': 'month_sin',
        'month_cos': 'month_cos',
        'florida_season': 'florida_season',
        'season_numeric': 'season_numeric',
        'season_sin': 'season_sin',
        'season_cos': 'season_cos',
        'is_dry_season': 'is_dry_season',
        'is_spring_transition': 'is_spring_transition',
        'is_wet_season': 'is_wet_season',
        'is_hurricane_season': 'is_hurricane_season',
        'thunderstorm': 'thunderstorm',
        'rain': 'rain',
        'heat_index': 'heat_index',
        'high_rain_risk': 'high_rain_risk',
        'high_wind_risk': 'high_wind_risk',
        'heat_wave_risk': 'heat_wave_risk',
        'hurricane_season': 'hurricane_season',
        'is_summer': 'is_summer',
        'summer_storm_risk': 'summer_storm_risk',
        'risk_score_0_100': 'risk_score_0_100',
        'risk_label': 'risk_label',
    }
    
    # Select only columns that exist in DataFrame and are in mapping
    available_cols = {k: v for k, v in column_mapping.items() if k in df.columns} # key-value pairs
    
    if not available_cols:
        raise ValueError("No matching columns found between DataFrame and database schema")
    
    # Prepare data for insertion
    df_to_insert = df[list(available_cols.keys())].copy()
    
    # Rename columns to match database
    df_to_insert = df_to_insert.rename(columns=available_cols)
    
    # Ensure start_time is datetime
    if 'start_time' in df_to_insert.columns:
        df_to_insert['start_time'] = pd.to_datetime(df_to_insert['start_time'])
    
    # Get database engine
    engine = get_engine()
    
    # Convert DataFrame to list of dicts for bulk insert
    records = df_to_insert.to_dict('records')
    
    if not records:
        return 0
    
    # Build upsert query
    columns = list(df_to_insert.columns)
    column_list = ', '.join(columns)
    placeholders = ', '.join([f':{col}' for col in columns])
    
    # Build UPDATE clause for ON CONFLICT (update all columns except city and start_time)
    update_cols = [col for col in columns if col not in ('city', 'start_time')]
    update_clause = ', '.join([f'{col} = EXCLUDED.{col}' for col in update_cols])
    
    upsert_sql = f"""
    INSERT INTO {table_name} ({column_list})
    VALUES ({placeholders})
    ON CONFLICT (city, start_time)
    DO UPDATE SET {update_clause}
    """
    
    # Execute upsert (one record at a time for proper parameter binding)
    rows_affected = 0
    with engine.begin() as conn:
        for record in records:
            # Convert any NaN/None values to None for SQL
            clean_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            result = conn.execute(text(upsert_sql), clean_record)
            rows_affected += result.rowcount
    
    return rows_affected
