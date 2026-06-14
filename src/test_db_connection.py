from sqlalchemy import text
from src.db import get_engine

engine = get_engine()

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1")).scalar()
    print("DB connected, SELECT 1 =", result)
