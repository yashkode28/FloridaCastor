"""Initialize the database schema."""
from __future__ import annotations

import pathlib
from pathlib import Path

from sqlalchemy import text

from src.db import get_engine


def init_db() -> None:
    """
    Initialize the database by running schema.sql.
    
    Creates all tables and indexes needed for the FloridaCastor application.
    """
    # Get the path to schema.sql
    project_root = Path(__file__).parent.parent
    schema_path = project_root / "db" / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema file not found at {schema_path}. "
            "Please ensure db/schema.sql exists."
        )
    
    # Read the schema SQL file
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    
    # Get database engine
    engine = get_engine()
    
    # Execute the schema
    with engine.begin() as conn:
        # Split by semicolons and execute each statement
        # (PostgreSQL can handle multiple statements, but this is safer)
        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
        
        for statement in statements:
            if statement:  # Skip empty statements
                conn.execute(text(statement))
    
    print("DB initialized ✅")
    print(f"Created tables: forecasts, predictions")
    print(f"Created indexes for performance")


if __name__ == "__main__":
    init_db()
