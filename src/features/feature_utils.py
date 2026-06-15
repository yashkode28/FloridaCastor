import pandas as pd
import numpy as np
from typing import Union

def parse_wind_speed(wind_speed: str) -> float:
    """
    Parse the wind speed from the NWS API response.
    Handles formats like "20 mph", "10 to 15 mph", "5-10 mph", etc.
    """
    if not wind_speed:
        return np.nan
    
    # Convert to string and extract all numeric values
    import re
    nums = re.findall(r'\d+', str(wind_speed))
    
    if not nums:
        return np.nan
    
    # Convert to integers and return average (handles ranges like "10 to 15")
    nums = [int(n) for n in nums]
    return sum(nums) / len(nums)

    # thunderstorm probability
def parse_thunderstorm_probability(probability: str) -> float:
    """
    Parse the thunderstorm probability from the NWS API response.
    """
    if not probability:
        return 0

    keywords = ["thunder", "storm", "t-storm"]
    return int(any(k in str(probability).lower() for k in keywords))

def has_rain(text):
    if not text:
        return 0
    return int("rain" in text.lower())

def categorize_florida_season(date: Union[pd.Timestamp, str, int]) -> str:
    """
    Categorize a date into Florida's seasonal categories.
    
    Categories:
    - 'dry/mild': November, December, January, February (cooler, drier months)
    - 'spring transition': March, April (transition from dry to wet season)
    - 'wet/thunderstorm': May, June, July (peak wet season with afternoon thunderstorms)
    - 'hurricane peak': August, September, October (peak hurricane season, still wet)
    
    Args:
        date: Can be a pandas Timestamp, datetime string, or month number (1-12)
    
    Returns:
        str: One of 'dry/mild', 'spring transition', 'wet/thunderstorm', 'hurricane peak'
    
    Examples:
        >>> categorize_florida_season(pd.Timestamp('2024-01-15'))
        'dry/mild'
        >>> categorize_florida_season(6)  # June
        'wet/thunderstorm'
    """
    # Handle different input types
    if isinstance(date, (int, float)):
        month = int(date)
    elif isinstance(date, str):
        date = pd.to_datetime(date)
        month = date.month
    elif isinstance(date, pd.Timestamp):
        month = date.month
    else:
        raise ValueError(f"Unsupported date type: {type(date)}")
    
    # Validate month
    if not (1 <= month <= 12):
        raise ValueError(f"Month must be between 1 and 12, got {month}")
    
    # Categorize based on Florida climate patterns
    if month in [11, 12, 1, 2]:  # November, December, January, February
        return 'dry/mild'
    elif month in [3, 4]:  # March, April
        return 'spring transition'
    elif month in [5, 6, 7]:  # May, June, July
        return 'wet/thunderstorm'
    elif month in [8, 9, 10]:  # August, September, October
        return 'hurricane peak'
    else:
        # Should never reach here, but just in case
        raise ValueError(f"Unexpected month value: {month}")

def add_season_features(df: pd.DataFrame, date_column: str = 'startTime') -> pd.DataFrame:
    """
    Add season-related features to a DataFrame with datetime column.
    
    Adds:
    - 'month': Month number (1-12)
    - 'month_sin': Cyclical encoding (sine) for month (12-month cycle)
    - 'month_cos': Cyclical encoding (cosine) for month (12-month cycle)
    - 'florida_season': Categorical season ('dry/mild', 'spring transition', etc.)
    - 'season_numeric': Numeric mapping of season (0-3)
    - 'season_sin': Cyclical encoding (sine) for season (4-season cycle)
    - 'season_cos': Cyclical encoding (cosine) for season (4-season cycle)
    - 'is_dry_season': Binary indicator for dry/mild season
    - 'is_wet_season': Binary indicator for wet/thunderstorm season
    - 'is_hurricane_season': Binary indicator for hurricane peak season
    - 'is_spring_transition': Binary indicator for spring transition
    
    Args:
        df: DataFrame with a datetime column
        date_column: Name of the datetime column (default: 'startTime')
    
    Returns:
        DataFrame with added season features
    """
    df = df.copy()
    
    # Ensure date column is datetime
    if date_column not in df.columns:
        raise ValueError(f"Column '{date_column}' not found in DataFrame")
    
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Extract month
    df['month'] = df[date_column].dt.month
    # Cyclical encoding for months (12-month cycle)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    
    # Categorize season
    df['florida_season'] = df[date_column].apply(categorize_florida_season)
    
    # Map seasons to numeric values for cyclical encoding (4 seasons)
    season_map = {
        'dry/mild': 0,
        'spring transition': 1,
        'wet/thunderstorm': 2,
        'hurricane peak': 3
    }
    df['season_numeric'] = df['florida_season'].map(season_map)
    
    # Cyclical encoding for seasons (4-season cycle)
    df["season_sin"] = np.sin(2 * np.pi * df["season_numeric"] / 4)
    df["season_cos"] = np.cos(2 * np.pi * df["season_numeric"] / 4)
    
    # Create binary indicators for each season
    df['is_dry_season'] = (df['florida_season'] == 'dry/mild').astype(int)
    df['is_spring_transition'] = (df['florida_season'] == 'spring transition').astype(int)
    df['is_wet_season'] = (df['florida_season'] == 'wet/thunderstorm').astype(int)
    df['is_hurricane_season'] = (df['florida_season'] == 'hurricane peak').astype(int)
    
    return df

# convert JSON to pandas DataFrame
def forecast_to_df(json_data: dict) -> pd.DataFrame:
    """
    Convert JSON data to a pandas DataFrame.
    """
    df = pd.DataFrame(json_data)

    # time features
    df['startTime'] = pd.to_datetime(df['startTime'])
    df['hours'] = df['startTime'].dt.hour
    
    # Add season features
    df = add_season_features(df, date_column='startTime')

    # numeric features
    df["wind_mph"] = df["windSpeed"].apply(parse_wind_speed)
    df["precip_prob"] = df["precipChance"].fillna(0) # missing values are 0
    df["humidity"] = df["humidity"].fillna(df["humidity"].mean())

    # Text-derived features
    df["thunderstorm"] = df["shortForecast"].apply(parse_thunderstorm_probability)
    df["rain"] = df["shortForecast"].apply(has_rain)

    # Drop raw text after extraction (optional)
    df = df.drop(columns=["windSpeed", "shortForecast"])

    return df
    
    # heat index approximation
def heat_index(temp_f, humidity):
    # Simple approximation
    return temp_f + 0.1 * humidity
    df['heat_index'] = heat_index(df['tempF'], df['humidity'])

# risk signals
def risk_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate risk signals from the DataFrame.
    """
    df['high_rain_risk'] = (df['precip_prob'] > 50).astype(int)
    df['high_wind_risk'] = (df['wind_mph'] > 15).astype(int)
    df['heat_wave_risk'] = (df['heat_index'] > 100).astype(int)

    df["hurricane_season"] = df["month"].isin([6,7,8,9,10,11]).astype(int)
    # Use is_wet_season if it exists, otherwise create it
    if 'is_wet_season' not in df.columns:
        df['is_wet_season'] = (df.get('florida_season', '') == 'wet/thunderstorm').astype(int)
    df['precip_risk'] = (df['precip_prob'] * (1 + 0.5 * df['is_wet_season'])) # higher disruption risk in wet season
    # Create heat_index if it doesn't exist
    if 'heat_index' not in df.columns and 'tempF' in df.columns and 'humidity' in df.columns:
        df['heat_index'] = heat_index(df['tempF'], df['humidity'])
    df['seasonal_heat_risk'] = (df['heat_index'] * (1 + 0.3 * df['is_wet_season'])) # higher humidity amplifies perceived heat, captures nonlinear discomfort
    # Summer = months 6, 7, 8 (June, July, August)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)
    df['summer_storm_risk'] = (df['thunderstorm'] * df['is_summer']) # higher disruption risk in summer thunderstorms
    
    return df

# training thresholds
def label_weather(row):
    if row["thunderstorm"] == 1:
        return 2  # No-go
    if row["high_rain_risk"] or row["dangerous_heat"]:
        return 1  # Caution
    return 0  # Good

    df['risk_label'] = df.apply(label_weather, axis=1)

def _clip01(x):
    return np.clip(x, 0.0, 1.0)

def build_cost_based_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a 0–100 composite risk score using cost-based weights.
    Assumes df already has:
      - precip_prob, wind_mph, heat_index
      - high_rain_risk, high_wind_risk, heat_wave_risk
      - summer_storm_risk, is_wet_season, hurricane_season
    """

    out = df.copy()

    # --- 1) Ensure precip_prob scale is 0–100 (adjust if you store 0–1)
    # If your precip_prob is already 0–1, comment this out.
    # Heuristic: if max <= 1.0, treat as fraction; else percent.
    if out["precip_prob"].max(skipna=True) <= 1.0:
        precip_pct = out["precip_prob"] * 100.0
    else:
        precip_pct = out["precip_prob"]

    # --- 2) Severity terms (0–1)
    # Precip severity: 20%->0, 80%->1 (linear ramp)
    precip_sev = _clip01((precip_pct - 20.0) / 60.0)

    # Heat severity: HI 90->0, 110->1
    heat_sev = _clip01((out["heat_index"] - 90.0) / 20.0)

    # Wind severity: 10 mph->0, 30 mph->1
    wind_sev = _clip01((out["wind_mph"] - 10.0) / 20.0)

    # --- 3) Hazard points (binary costs)
    # These are your "false negative is expensive" flags
    hazard_points = (
        5.0 * out["summer_storm_risk"] +  # lightning/storm disruption
        4.0 * out["heat_wave_risk"] +
        3.0 * out["high_wind_risk"] +
        2.0 * out["high_rain_risk"]
    )

    # --- 4) Severity points (adds nuance even when flags don't trip)
    severity_points = (
        2.0 * precip_sev +
        2.0 * heat_sev +
        1.0 * wind_sev
    )

    raw = hazard_points + severity_points

    # --- 5) Context multipliers (not direct points)
    # Wet season amplifies rain/storm disruption; hurricane season bumps baseline
    context_mult = (
        1.0 +
        0.15 * out["is_wet_season"] +
        0.10 * out["hurricane_season"]
    )

    raw_adj = raw * context_mult

    # --- 6) Map to 0–100
    # Max-ish raw: hazards up to ~14 plus severities up to ~5 → ~19; with multipliers ~1.25 → ~24
    # Use a cap for stability.
    cap = 25.0
    out["risk_score_0_100"] = 100.0 * _clip01(raw_adj / cap)

    # Helpful debugging columns (optional; keep while developing)
    out["risk_raw"] = raw
    out["risk_raw_adj"] = raw_adj
    out["precip_severity_0_1"] = precip_sev
    out["heat_severity_0_1"] = heat_sev
    out["wind_severity_0_1"] = wind_sev

    return out

def score_to_label(score):
    # conservative thresholds for safety
    if score >= 70:
        return 2  # No-go
    elif score >= 35:
        return 1  # Caution
    return 0      # Good


# ---- Deterministic, model-free explanations -------------------------------

# Fixed display priority for deterministic tie-breaking (lower shows first).
_FACTOR_ORDER = {"storm": 0, "heat": 1, "precip": 2, "wind": 3, "humidity": 4, "temp": 5}


def explain_risk_factors(row, top_n: int = 5, min_n: int = 3) -> list:
    """
    Produce a deterministic, plain-English explanation of one forecast hour's risk.

    No model or external API is involved: every factor is derived directly from the
    same weather features and risk signals used by build_cost_based_risk_score().
    Each factor reports `score`, its share of that hour's 0-100 risk score, so the
    returned list doubles as a ranked list of the biggest risk drivers.

    Args:
        row: a DataFrame row (Series) that has already passed through risk_signals()
             and build_cost_based_risk_score() — typically the peak-risk hour.

    Returns:
        A list (3-5 items) sorted by importance, each:
            {"text": str, "tone": "warn"|"good", "score": float, "top": bool}
        `tone` drives the UI icon (warn -> warning, good -> check). The single
        largest risk driver is flagged with "top": True.
    """
    def num(v, default=0.0):
        try:
            f = float(v)
            return default if np.isnan(f) else f
        except (TypeError, ValueError):
            return default

    humidity = num(row.get("humidity"))
    tempf = num(row.get("tempF"))
    storm = int(num(row.get("thunderstorm")))

    high_rain = int(num(row.get("high_rain_risk")))
    high_wind = int(num(row.get("high_wind_risk")))
    heat_wave = int(num(row.get("heat_wave_risk")))
    storm_haz = num(row.get("summer_storm_risk"))

    precip_sev = num(row.get("precip_severity_0_1"))
    heat_sev = num(row.get("heat_severity_0_1"))
    wind_sev = num(row.get("wind_severity_0_1"))

    # Same context multiplier and cap used by build_cost_based_risk_score().
    context_mult = 1.0 + 0.15 * num(row.get("is_wet_season")) + 0.10 * num(row.get("hurricane_season"))
    cap = 25.0

    def share(points):
        # Portion of the final 0-100 score attributable to this factor (pre-clip).
        return round(100.0 * points * context_mult / cap, 1)

    factors = []

    # --- Thunderstorm / storm (hazard: 5 * summer_storm_risk) ---
    if storm:
        factors.append({"key": "storm", "tone": "warn",
                        "text": "Thunderstorm activity expected", "points": 5.0 * storm_haz})
    else:
        factors.append({"key": "storm", "tone": "good",
                        "text": "No thunderstorm activity", "points": 0.0})

    # --- Heat index (hazard: 4 * heat_wave_risk; severity: 2 * heat_sev) ---
    heat_pts = 4.0 * heat_wave + 2.0 * heat_sev
    if heat_wave:
        factors.append({"key": "heat", "tone": "warn", "text": "Dangerous heat index", "points": heat_pts})
    elif heat_sev > 0:
        factors.append({"key": "heat", "tone": "warn", "text": "Elevated heat index", "points": heat_pts})
    else:
        factors.append({"key": "heat", "tone": "good", "text": "Comfortable heat index", "points": 0.0})

    # --- Precipitation (hazard: 2 * high_rain_risk; severity: 2 * precip_sev) ---
    precip_pts = 2.0 * high_rain + 2.0 * precip_sev
    if high_rain:
        factors.append({"key": "precip", "tone": "warn", "text": "High precipitation probability", "points": precip_pts})
    elif precip_sev > 0:
        factors.append({"key": "precip", "tone": "warn", "text": "Moderate precipitation risk", "points": precip_pts})
    else:
        factors.append({"key": "precip", "tone": "good", "text": "Low precipitation probability", "points": 0.0})

    # --- Wind (hazard: 3 * high_wind_risk; severity: 1 * wind_sev) ---
    wind_pts = 3.0 * high_wind + 1.0 * wind_sev
    if high_wind:
        factors.append({"key": "wind", "tone": "warn", "text": "Strong winds forecast", "points": wind_pts})
    elif wind_sev > 0:
        factors.append({"key": "wind", "tone": "warn", "text": "Breezy conditions", "points": wind_pts})
    else:
        factors.append({"key": "wind", "tone": "good", "text": "Low wind speeds", "points": 0.0})

    # --- Humidity (context only: feeds the heat index, not scored directly) ---
    if humidity >= 80:
        factors.append({"key": "humidity", "tone": "warn", "text": "Elevated humidity", "points": 0.0})
    elif 0 < humidity <= 55:
        factors.append({"key": "humidity", "tone": "good", "text": "Comfortable humidity", "points": 0.0})

    # --- Temperature (positive signal only; heat risk handled via heat index) ---
    if 60 <= tempf <= 85:
        factors.append({"key": "temp", "tone": "good", "text": "Mild temperatures", "points": 0.0})

    for f in factors:
        f["score"] = share(f["points"])
        f["order"] = _FACTOR_ORDER.get(f["key"], 99)

    # Warnings first, ranked by actual score contribution (biggest driver on top);
    # positives after, in fixed order. Deterministic given identical input.
    warns = sorted((f for f in factors if f["tone"] == "warn"), key=lambda f: (-f["points"], f["order"]))
    goods = sorted((f for f in factors if f["tone"] == "good"), key=lambda f: f["order"])
    ordered = (warns + goods)[:max(top_n, min_n)][:top_n]

    if ordered and ordered[0]["tone"] == "warn" and ordered[0]["points"] > 0:
        ordered[0]["top"] = True

    return [
        {"text": f["text"], "tone": f["tone"], "score": f["score"], "top": f.get("top", False)}
        for f in ordered
    ]