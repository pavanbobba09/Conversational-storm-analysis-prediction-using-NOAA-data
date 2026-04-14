"""
NOAA Storm Events Database Package
===================================

PostgreSQL database integration for NOAA storm events data.

Components:
-----------
- models.py: SQLAlchemy ORM models for storm_events table
- connection.py: Database connection pooling and session management
- migrate_to_postgres.py: Data migration script (parquet -> PostgreSQL)

Usage:
------
    from src.database.connection import get_session
    from src.database.models import StormEvent

    # Query storms
    with get_session() as session:
        tornadoes = session.query(StormEvent).filter(
            StormEvent.event_type == 'Tornado'
        ).all()

Author: NOAA Storm Analytics System
Version: 1.0.0
"""

from .models import StormEvent, Base
from .connection import (
    engine,
    SessionLocal,
    get_session,
    get_db_url,
    init_database
)

__all__ = [
    'StormEvent',
    'Base',
    'engine',
    'SessionLocal',
    'get_session',
    'get_db_url',
    'init_database'
]

__version__ = '1.0.0'
