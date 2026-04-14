"""
SQLAlchemy ORM Models
=====================

SQLAlchemy ORM definition for the NOAA Storm Events database.

Models:
-------
- StormEvent: Complete NOAA storm event record with all 54 columns + PostGIS

Usage:
------
    from src.database.models import StormEvent
    from src.database.connection import get_session

    # Query tornadoes in Texas
    with get_session() as session:
        tornadoes = session.query(StormEvent).filter(
            StormEvent.event_type == 'Tornado',
            StormEvent.state == 'TX'
        ).all()

        for tornado in tornadoes:
            print(f"{tornado.event_id}: {tornado.cz_name}")

Author: NOAA Storm Analytics System
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, BigInteger, Integer, String, Numeric, Text,
    TIMESTAMP, CheckConstraint, Index, func
)
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography

# Base class for all models
Base = declarative_base()


class StormEvent(Base):
    """
    NOAA Storm Event ORM Model.

    Maps to the storm_events table in PostgreSQL.
    Contains all 54 NOAA columns plus PostGIS geography columns.

    Table Structure:
    ----------------
    - Event Identifiers: event_id (PK), episode_id
    - Event Type: event_type (Tornado, Hurricane, etc.)
    - Temporal: begin_date_time, end_date_time, year, month_name
    - Location: state, cz_name, begin_lat, begin_lon, etc.
    - Impact: deaths_direct, injuries_direct, total_damage, etc.
    - Storm Characteristics: magnitude, tor_f_scale, flood_cause, etc.
    - Narratives: episode_narrative, event_narrative
    - PostGIS: begin_location, end_location (geography points)

    Example:
    --------
        >>> storm = session.query(StormEvent).filter(
        ...     StormEvent.event_id == 123456
        ... ).first()
        >>> print(f"{storm.event_type} in {storm.state}")
        Tornado in TX
        >>> print(f"Damage: ${storm.total_damage:,.0f}")
        Damage: $1,500,000
    """

    __tablename__ = 'storm_events'

    # ========================================================================
    # Event Identifiers
    # ========================================================================
    event_id = Column(BigInteger, primary_key=True, nullable=False,
                      comment='NOAA unique event identifier')
    episode_id = Column(BigInteger, comment='Episode identifier (multi-event)')

    # ========================================================================
    # Event Type & Classification
    # ========================================================================
    event_type = Column(String(50), nullable=False, index=True,
                        comment='Storm type: Tornado, Hurricane, Flood, etc.')

    # ========================================================================
    # Temporal Information
    # ========================================================================
    begin_date_time = Column(TIMESTAMP, index=True,
                             comment='Event start timestamp')
    end_date_time = Column(TIMESTAMP,
                           comment='Event end timestamp')
    year = Column(Integer, nullable=False, index=True,
                  comment='Year (1996-2025)')
    month_name = Column(String(20), comment='Month name')

    # ========================================================================
    # Geographic Information - Administrative
    # ========================================================================
    state = Column(String(2), index=True,
                   comment='US state code (TX, CA, etc.)')
    state_fips = Column(Integer, comment='FIPS state code')
    cz_type = Column(String(1), comment='County zone type (C/Z/M)')
    cz_fips = Column(Integer, comment='County zone FIPS code')
    cz_name = Column(String(100), index=True,
                     comment='County/Zone name')
    wfo = Column(String(10), comment='Weather Forecast Office')

    # ========================================================================
    # Geographic Information - Coordinates
    # ========================================================================
    begin_lat = Column(Numeric(10, 6),
                       comment='Begin latitude (degrees N)')
    begin_lon = Column(Numeric(10, 6),
                       comment='Begin longitude (degrees W, negative)')
    end_lat = Column(Numeric(10, 6),
                     comment='End latitude')
    end_lon = Column(Numeric(10, 6),
                     comment='End longitude')

    # PostGIS Geography Columns (for spatial queries)
    begin_location = Column(Geography('POINT', srid=4326),
                            comment='Begin point (PostGIS geography)')
    end_location = Column(Geography('POINT', srid=4326),
                          comment='End point (PostGIS geography)')

    # ========================================================================
    # Impact Statistics - Casualties
    # ========================================================================
    deaths_direct = Column(Integer, default=0,
                           comment='Direct fatalities')
    deaths_indirect = Column(Integer, default=0,
                             comment='Indirect fatalities')
    injuries_direct = Column(Integer, default=0,
                             comment='Direct injuries')
    injuries_indirect = Column(Integer, default=0,
                               comment='Indirect injuries')

    # ========================================================================
    # Impact Statistics - Economic Damage
    # ========================================================================
    damage_property = Column(String(20),
                             comment='Property damage (original text: 10K, 5M)')
    damage_crops = Column(String(20),
                          comment='Crop damage (original text)')
    damage_property_num = Column(Numeric(15, 2), default=0,
                                 comment='Property damage (numeric, USD)')
    damage_crops_num = Column(Numeric(15, 2), default=0,
                              comment='Crop damage (numeric, USD)')
    total_damage = Column(Numeric(15, 2), default=0, index=True,
                          comment='Total damage (property + crops, USD)')

    # ========================================================================
    # Storm Characteristics - Magnitude & Intensity
    # ========================================================================
    magnitude = Column(Numeric(10, 2), comment='Storm magnitude')
    magnitude_type = Column(String(10), comment='Magnitude unit (EG, MS, etc.)')

    # Tornado-Specific
    tor_f_scale = Column(String(5), comment='Fujita scale (F0-F5, EF0-EF5)')
    tor_length = Column(Numeric(10, 2), comment='Tornado path length (miles)')
    tor_width = Column(Numeric(10, 2), comment='Tornado path width (yards)')
    tor_other_wfo = Column(String(10), comment='Other WFO (if tornado crosses)')
    tor_other_cz_state = Column(String(2),
                                comment='Other state (if crosses boundary)')
    tor_other_cz_fips = Column(Integer, comment='Other county FIPS')
    tor_other_cz_name = Column(String(100), comment='Other county name')

    # Flood-Specific
    flood_cause = Column(String(50), comment='Cause of flooding')

    # ========================================================================
    # Data Source & Quality
    # ========================================================================
    source = Column(String(50), comment='Data source')
    begin_range = Column(Integer, comment='Begin range (distance accuracy)')
    begin_azimuth = Column(String(10), comment='Begin direction (N, NE, etc.)')
    end_range = Column(Integer, comment='End range')
    end_azimuth = Column(String(10), comment='End direction')

    # ========================================================================
    # Event Narratives & Descriptions
    # ========================================================================
    episode_narrative = Column(Text, comment='Episode-level description')
    event_narrative = Column(Text, comment='Event-level description')

    # ========================================================================
    # Additional NOAA Columns
    # ========================================================================
    begin_yearmonth = Column(Integer, comment='YYYYMM format')
    begin_day = Column(Integer, comment='Day of month (1-31)')
    begin_time = Column(String(10), comment='Time (HHMM format)')
    end_yearmonth = Column(Integer, comment='End YYYYMM')
    end_day = Column(Integer, comment='End day')
    end_time = Column(String(10), comment='End time (HHMM)')

    category = Column(String(20), comment='Storm category (1-5 for hurricanes)')

    # Timestamp Metadata
    data_source = Column(String(100),
                         comment='Source: NOAA Storm Events Database')
    begin_location_txt = Column(String(200),
                                comment='Begin location description')
    end_location_txt = Column(String(200),
                              comment='End location description')

    # ========================================================================
    # System Metadata
    # ========================================================================
    created_at = Column(TIMESTAMP, default=datetime.now,
                        comment='Record creation timestamp')
    updated_at = Column(TIMESTAMP, default=datetime.now,
                        onupdate=datetime.now,
                        comment='Last update timestamp')

    # ========================================================================
    # Table-level Configuration
    # ========================================================================
    __table_args__ = (
        # Composite indexes
        Index('idx_event_state_year', 'event_type', 'state', 'year'),
        Index('idx_state_county', 'state', 'cz_name'),
        Index('idx_year_month', 'year', 'month_name'),

        # Partial indexes (PostgreSQL specific - only index rows matching condition)
        Index('idx_has_deaths', (deaths_direct + deaths_indirect),
              postgresql_where=(deaths_direct + deaths_indirect) > 0),
        Index('idx_has_injuries', (injuries_direct + injuries_indirect),
              postgresql_where=(injuries_direct + injuries_indirect) > 0),
        Index('idx_has_damage', total_damage,
              postgresql_where=total_damage > 0),

        # PostGIS spatial indexes
        Index('idx_begin_location_gist', begin_location,
              postgresql_using='gist'),
        Index('idx_end_location_gist', end_location,
              postgresql_using='gist'),

        # Check constraints
        CheckConstraint('begin_date_time <= end_date_time OR end_date_time IS NULL',
                        name='check_date_range'),
        CheckConstraint('year BETWEEN 1996 AND 2030',
                        name='check_year_range'),
        CheckConstraint('total_damage >= 0',
                        name='check_damage_non_negative'),
        CheckConstraint('deaths_direct >= 0 AND deaths_indirect >= 0',
                        name='check_deaths_non_negative'),
        CheckConstraint('injuries_direct >= 0 AND injuries_indirect >= 0',
                        name='check_injuries_non_negative'),

        # Table comment
        {
            'comment': 'NOAA Storm Events Database (1996-2025): Complete dataset '
                       'with 1,117,547 events and all 54 original NOAA columns preserved'
        }
    )

    # ========================================================================
    # Properties & Methods
    # ========================================================================

    @property
    def total_deaths(self) -> int:
        """Calculate total deaths (direct + indirect)."""
        return (self.deaths_direct or 0) + (self.deaths_indirect or 0)

    @property
    def total_injuries(self) -> int:
        """Calculate total injuries (direct + indirect)."""
        return (self.injuries_direct or 0) + (self.injuries_indirect or 0)

    @property
    def total_casualties(self) -> int:
        """Calculate total casualties (deaths + injuries)."""
        return self.total_deaths + self.total_injuries

    @property
    def damage_formatted(self) -> str:
        """Format total damage as currency string."""
        if self.total_damage:
            return f"${self.total_damage:,.0f}"
        return "$0"

    @property
    def location_str(self) -> str:
        """Get formatted location string."""
        if self.cz_name and self.state:
            return f"{self.cz_name}, {self.state}"
        elif self.state:
            return self.state
        return "Unknown"

    @property
    def date_str(self) -> str:
        """Get formatted date string."""
        if self.begin_date_time:
            return self.begin_date_time.strftime("%Y-%m-%d %H:%M")
        return "Unknown"

    def __repr__(self) -> str:
        """String representation of StormEvent."""
        return (
            f"<StormEvent("
            f"id={self.event_id}, "
            f"type='{self.event_type}', "
            f"location='{self.location_str}', "
            f"date='{self.date_str}'"
            f")>"
        )

    def to_dict(self) -> dict:
        """
        Convert StormEvent to dictionary.

        Returns:
            dict: Dictionary with all column values

        Example:
            >>> storm = session.query(StormEvent).first()
            >>> data = storm.to_dict()
            >>> print(data['event_type'])
            Tornado
        """
        return {
            'event_id': self.event_id,
            'episode_id': self.episode_id,
            'event_type': self.event_type,
            'begin_date_time': self.begin_date_time,
            'end_date_time': self.end_date_time,
            'year': self.year,
            'month_name': self.month_name,
            'state': self.state,
            'cz_name': self.cz_name,
            'begin_lat': float(self.begin_lat) if self.begin_lat else None,
            'begin_lon': float(self.begin_lon) if self.begin_lon else None,
            'end_lat': float(self.end_lat) if self.end_lat else None,
            'end_lon': float(self.end_lon) if self.end_lon else None,
            'deaths_direct': self.deaths_direct,
            'deaths_indirect': self.deaths_indirect,
            'injuries_direct': self.injuries_direct,
            'injuries_indirect': self.injuries_indirect,
            'total_damage': float(self.total_damage) if self.total_damage else 0,
            'magnitude': float(self.magnitude) if self.magnitude else None,
            'tor_f_scale': self.tor_f_scale,
            'flood_cause': self.flood_cause,
            'event_narrative': self.event_narrative,
            # Add more fields as needed
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_tables(engine):
    """
    Create all tables defined in Base.

    Args:
        engine: SQLAlchemy engine instance

    Example:
        >>> from src.database.connection import engine
        >>> from src.database.models import create_tables
        >>> create_tables(engine)
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def drop_tables(engine):
    """
    Drop all tables defined in Base.

    WARNING: This will delete all data!

    Args:
        engine: SQLAlchemy engine instance

    Example:
        >>> from src.database.connection import engine
        >>> from src.database.models import drop_tables
        >>> drop_tables(engine)
    """
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


if __name__ == "__main__":
    # Print model information
    print("NOAA Storm Events ORM Model")
    print("=" * 60)
    print(f"Table: {StormEvent.__tablename__}")
    print(f"Columns: {len(StormEvent.__table__.columns)}")
    print("\nColumn Details:")
    print("-" * 60)
    for col in StormEvent.__table__.columns:
        col_type = str(col.type)
        nullable = "NULL" if col.nullable else "NOT NULL"
        pk = " (PK)" if col.primary_key else ""
        print(f"  {col.name:25} {col_type:20} {nullable}{pk}")

    print("\nIndexes:")
    print("-" * 60)
    for idx in StormEvent.__table__.indexes:
        print(f"  {idx.name}")

    print("\n✓ Model definition loaded successfully")
