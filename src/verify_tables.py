from sqlalchemy import text
from src.db import get_engine

engine = get_engine()

sql = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"""

with engine.connect() as conn:
    tables = conn.execute(text(sql)).fetchall()
    print("Tables:", [t[0] for t in tables])
