"""Database connection utilities for FloridaCastor."""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.engine import URL


def get_engine(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> Engine:
    """
    Create and return a SQLAlchemy engine for PostgreSQL.

    If DATABASE_URL is set (e.g. postgresql+psycopg2://user:pass@host:5432/dbname),
    it is used as-is and individual DB_* arguments are ignored.

    Otherwise reads connection parameters from environment variables or uses defaults:
    - DB_HOST (default: localhost)
    - DB_PORT (default: 5432)
    - DB_USER (default: weather)
    - DB_PASSWORD (default: weather_pw)
    - DB_NAME (default: weather_db)
    
    Args:
        host: Database host (overrides DB_HOST env var)
        port: Database port (overrides DB_PORT env var)
        user: Database user (overrides DB_USER env var)
        password: Database password (overrides DB_PASSWORD env var)
        database: Database name (overrides DB_NAME env var)
    
    Returns:
        SQLAlchemy Engine instance
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

    # Get connection parameters from environment or use defaults
    db_host = host or os.getenv("DB_HOST", "localhost")
    db_port = port or int(os.getenv("DB_PORT", "5432"))
    db_user = user or os.getenv("DB_USER", "weather")
    db_password = password or os.getenv("DB_PASSWORD", "weather_pw")
    db_name = database or os.getenv("DB_NAME", "weather_db")
    
    # Create connection URL
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_name,
    )
    
    # Create engine with connection pooling
    engine = create_engine(
        url,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging
    )
    
    return engine
