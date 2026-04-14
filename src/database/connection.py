"""
PostgreSQL Connection Management
=================================

Handles database connection pooling and session management for the NOAA
Storm Events database.

Features:
---------
- Connection pooling (5 permanent + 10 overflow connections)
- Pre-ping to avoid stale connections
- Context manager for safe session handling
- Environment-based configuration

Usage:
------
    from src.database.connection import get_session

    # Safe session handling with context manager
    with get_session() as session:
        results = session.query(StormEvent).all()
        # Session automatically closed after use

Configuration:
--------------
Set these environment variables in .env:

    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=noaa_storms
    DB_USER=postgres
    DB_PASSWORD=your_password
    DB_POOL_SIZE=5
    DB_MAX_OVERFLOW=10
    DB_POOL_TIMEOUT=30

Author: NOAA Storm Analytics System
"""

import os
from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """
    Get PostgreSQL connection URL from environment variables.

    Returns:
        str: PostgreSQL connection URL in format:
             postgresql://user:password@host:port/database

    Environment Variables:
        DB_HOST: PostgreSQL server host (default: localhost)
        DB_PORT: PostgreSQL server port (default: 5432)
        DB_NAME: Database name (default: noaa_storms)
        DB_USER: Database user (default: postgres)
        DB_PASSWORD: Database password (required)

    Example:
        >>> url = get_db_url()
        >>> print(url)
        postgresql://postgres:password@localhost:5432/noaa_storms
    """
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'noaa_storms')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', '')

    # Validate password is set
    if not password:
        logger.warning(
            "DB_PASSWORD not set in environment. Using empty password. "
            "This may work for local development but is not recommended."
        )

    url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return url


def create_db_engine():
    """
    Create SQLAlchemy engine with connection pooling.

    Connection Pool Configuration:
        - pool_size: 5 permanent connections
        - max_overflow: 10 additional connections when needed
        - pool_timeout: 30 seconds to wait for available connection
        - pool_pre_ping: Test connections before use (avoid stale connections)
        - pool_recycle: Recycle connections after 1 hour

    Returns:
        Engine: SQLAlchemy engine instance

    Raises:
        OperationalError: If cannot connect to database
    """
    db_url = get_db_url()

    # Connection pool settings
    pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
    max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))

    logger.info(f"Creating database engine for: {db_url.split('@')[1]}")
    logger.info(
        f"Connection pool: size={pool_size}, "
        f"max_overflow={max_overflow}, "
        f"timeout={pool_timeout}s"
    )

    try:
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,  # Verify connection before use
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False,          # Set to True for SQL query logging
        )

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")

        return engine

    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error(
            "Please check your .env file has correct database credentials"
        )
        raise


# Create global engine instance
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Provides safe session handling with automatic:
    - Session creation
    - Commit on success
    - Rollback on error
    - Session closure

    Yields:
        Session: SQLAlchemy session instance

    Example:
        >>> with get_session() as session:
        ...     results = session.query(StormEvent).all()
        ...     # Session auto-commits if no errors
        ...     # Session auto-rolls back on exception
        ...     # Session always closes after use

    Raises:
        Exception: Re-raises any exceptions after rollback
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session rollback due to error: {e}")
        raise
    finally:
        session.close()


def init_database():
    """
    Initialize database connection and verify it's working.

    This function:
    1. Creates database engine
    2. Tests connection
    3. Verifies PostGIS extension is available
    4. Checks storm_events table exists

    Returns:
        bool: True if database is ready, False otherwise

    Example:
        >>> if init_database():
        ...     print("Database ready!")
        ... else:
        ...     print("Database not configured")
    """
    try:
        with get_session() as session:
            # Test basic query
            result = session.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"PostgreSQL version: {version.split(',')[0]}")

            # Check PostGIS
            result = session.execute(text("SELECT PostGIS_Version()"))
            postgis_version = result.fetchone()[0]
            logger.info(f"PostGIS version: {postgis_version}")

            # Check storm_events table exists
            result = session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'storm_events'"
            ))
            table_exists = result.fetchone()[0] > 0

            if table_exists:
                # Get record count
                result = session.execute(text("SELECT COUNT(*) FROM storm_events"))
                record_count = result.fetchone()[0]
                logger.info(
                    f"✓ storm_events table exists with {record_count:,} records"
                )
            else:
                logger.warning(
                    "⚠ storm_events table does not exist. "
                    "Run schema/create_tables.sql first."
                )
                return False

        logger.info("✓ Database initialization successful")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


# Optional: Add event listeners for debugging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections."""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log connection return to pool."""
    logger.debug("Connection returned to pool")


# Cleanup function for graceful shutdown
def close_database():
    """
    Close all database connections and dispose engine.

    Call this function when shutting down the application to ensure
    all connections are properly closed.

    Example:
        >>> import atexit
        >>> atexit.register(close_database)
    """
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("✓ Database connections closed")


if __name__ == "__main__":
    # Test database connection
    import sys
    logging.basicConfig(level=logging.INFO)

    print("Testing database connection...")
    if init_database():
        print("\n✓ Database connection successful!")
        print(f"Engine: {engine}")
        print(f"Pool size: {engine.pool.size()}")
        sys.exit(0)
    else:
        print("\n✗ Database connection failed!")
        print("Please check your .env configuration")
        sys.exit(1)
