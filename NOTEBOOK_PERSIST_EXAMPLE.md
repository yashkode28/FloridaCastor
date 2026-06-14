# How to Persist DataFrame to Database

## Option 1: Add to Notebook (Recommended for Testing)

Add this cell **after** your risk scoring cell (where `df` has all features including `risk_label`):

```python
# ============================================================================
# PERSIST TO DATABASE
# ============================================================================
from src.persist import upsert_weather_hourly

# IMPORTANT: Add city column if not already present
# Replace "Miami" with the actual city you're processing
city_name = "Miami"  # Change this to match your data
df["city"] = city_name

# Upsert to database
n = upsert_weather_hourly(df, city=city_name)
print(f"✅ Upserted {n} rows to database")
```

## Option 2: Use Standalone Script (Recommended for Production)

Run the complete pipeline from command line:

```bash
# Process a single city
python -m src.fetch_and_persist Miami

# Process all cities
python -m src.fetch_and_persist --all
```

This script will:
1. Fetch forecast data from NWS API
2. Apply all feature engineering
3. Calculate risk scores
4. Persist to database

## Where to Build the DataFrame

### In Notebook:
- Your existing cells already build `df_cleaned` from `forecast_to_df()`
- Then you add risk scoring to get final `df`
- **Add the persist cell right after risk scoring**

### In Standalone Script:
- Use `src/fetch_and_persist.py` which handles everything end-to-end
