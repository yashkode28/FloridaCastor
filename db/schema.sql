-- FloridaCastor Database Schema
-- Stores weather forecasts, features, and risk predictions

-- Forecasts table: stores raw and processed forecast data
CREATE TABLE IF NOT EXISTS forecasts (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Raw weather data
    temp_f INTEGER,
    wind_direction VARCHAR(10),
    precip_chance INTEGER,
    humidity INTEGER,
    
    -- Processed features
    wind_mph DECIMAL(5, 2),
    precip_prob DECIMAL(5, 2),
    hours INTEGER,
    month INTEGER,
    month_sin DECIMAL(10, 6),
    month_cos DECIMAL(10, 6),
    florida_season VARCHAR(50),
    season_numeric INTEGER,
    season_sin DECIMAL(10, 6),
    season_cos DECIMAL(10, 6),
    
    -- Binary indicators
    is_dry_season INTEGER,
    is_spring_transition INTEGER,
    is_wet_season INTEGER,
    is_hurricane_season INTEGER,
    thunderstorm INTEGER,
    rain INTEGER,
    
    -- Risk features
    heat_index DECIMAL(5, 2),
    high_rain_risk INTEGER,
    high_wind_risk INTEGER,
    heat_wave_risk INTEGER,
    hurricane_season INTEGER,
    is_summer INTEGER,
    summer_storm_risk INTEGER,
    
    -- Risk scores and labels
    risk_score_0_100 DECIMAL(5, 2),
    risk_label INTEGER,  -- 0=Good, 1=Caution, 2=No-go
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for common queries
    CONSTRAINT unique_forecast UNIQUE (city, start_time)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_forecasts_city ON forecasts(city);
CREATE INDEX IF NOT EXISTS idx_forecasts_start_time ON forecasts(start_time);
CREATE INDEX IF NOT EXISTS idx_forecasts_risk_label ON forecasts(risk_label);
CREATE INDEX IF NOT EXISTS idx_forecasts_season ON forecasts(florida_season);
CREATE INDEX IF NOT EXISTS idx_forecasts_created_at ON forecasts(created_at);

-- Historical predictions table (optional - for tracking model predictions over time)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    forecast_id INTEGER REFERENCES forecasts(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    predicted_label INTEGER NOT NULL,
    predicted_score DECIMAL(5, 2),
    confidence DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_forecast_id ON predictions(forecast_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model_name ON predictions(model_name);
