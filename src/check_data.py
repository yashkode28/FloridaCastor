from sqlalchemy import text
from src.db import get_engine

engine = get_engine()

with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM forecasts")).scalar()
    print("Row count:", count)

    sample = conn.execute(text("""
        SELECT city, start_time, temp_f, precip_prob, wind_mph, risk_score_0_100, risk_label
        FROM forecasts
        ORDER BY start_time DESC
        LIMIT 5;
    """)).fetchall()

    print("\nLatest 5 rows:")
    for row in sample:
        print(row)
