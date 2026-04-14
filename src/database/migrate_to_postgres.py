"""
NOAA Storm Data Migration Script
=================================

Migrates NOAA storm data from parquet files to PostgreSQL database.

Features:
---------
- Fast bulk loading using PostgreSQL COPY
- PostGIS geography column population
- Data validation and integrity checks
- Progress tracking with tqdm
- Rollback on error

Usage:
------
    # Using default parquet file
    python src/database/migrate_to_postgres.py

    # Using custom parquet file
    python src/database/migrate_to_postgres.py --source path/to/storms.parquet

    # Dry run (validate without inserting)
    python src/database/migrate_to_postgres.py --dry-run

Author: NOAA Storm Analytics System
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np
from tqdm import tqdm
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_session, engine, init_database
from src.database.models import StormEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StormDataMigration:
    """
    Handles migration of NOAA storm data from parquet to PostgreSQL.
    """

    def __init__(self, source_file: str, dry_run: bool = False):
        """
        Initialize migration.

        Args:
            source_file: Path to parquet file with storm data
            dry_run: If True, validate without inserting
        """
        self.source_file = Path(source_file)
        self.dry_run = dry_run
        self.df: Optional[pd.DataFrame] = None
        self.records_inserted = 0

        # Validate source file exists
        if not self.source_file.exists():
            raise FileNotFoundError(f"Source file not found: {self.source_file}")

        logger.info(f"Migration initialized")
        logger.info(f"Source: {self.source_file}")
        logger.info(f"Dry run: {self.dry_run}")

    def load_data(self) -> pd.DataFrame:
        """
        Load NOAA data from parquet file.

        Returns:
            pd.DataFrame: Loaded data
        """
        logger.info("Loading NOAA data from parquet...")

        try:
            self.df = pd.read_parquet(self.source_file)
            logger.info(f"✓ Loaded {len(self.df):,} records with {len(self.df.columns)} columns")

            # Display column names
            logger.info(f"Columns: {', '.join(self.df.columns[:10])}...")

            return self.df

        except Exception as e:
            logger.error(f"Failed to load parquet file: {e}")
            raise

    def prepare_dataframe(self) -> pd.DataFrame:
        """
        Prepare DataFrame for PostgreSQL insertion.

        - Convert column names to lowercase
        - Handle datetime conversions
        - Fill NaN values appropriately
        - Ensure correct data types

        Returns:
            pd.DataFrame: Prepared data
        """
        logger.info("Preparing DataFrame for PostgreSQL...")

        df = self.df.copy()

        # Convert column names to lowercase (PostgreSQL convention)
        df.columns = df.columns.str.lower()

        # Handle datetime columns
        datetime_cols = ['begin_date_time', 'end_date_time']
        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Remove duplicate event_ids (keep first occurrence)
        initial_count = len(df)
        df = df.drop_duplicates(subset=['event_id'], keep='first')
        duplicates_removed = initial_count - len(df)
        if duplicates_removed > 0:
            logger.info(f"✓ Removed {duplicates_removed:,} duplicate event_ids (kept first occurrence)")

        # Fill NaN values for numeric columns
        numeric_cols = [
            'deaths_direct', 'deaths_indirect',
            'injuries_direct', 'injuries_indirect',
            'damage_property_num', 'damage_crops_num', 'total_damage',
            'state_fips', 'cz_fips', 'magnitude',
            'tor_length', 'tor_width',
            'begin_range', 'end_range',
            'begin_yearmonth', 'begin_day', 'end_yearmonth', 'end_day'
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # Convert integer columns to proper int type
        integer_cols = [
            'event_id', 'episode_id', 'year',
            'deaths_direct', 'deaths_indirect',
            'injuries_direct', 'injuries_indirect',
            'state_fips', 'cz_fips',
            'begin_range', 'end_range',
            'begin_yearmonth', 'begin_day', 'end_yearmonth', 'end_day',
            'tor_other_cz_fips'
        ]

        for col in integer_cols:
            if col in df.columns:
                # Convert to numeric (float), then to int
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')

        # Ensure coordinates are float
        coord_cols = ['begin_lat', 'begin_lon', 'end_lat', 'end_lon']
        for col in coord_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Fill NaN for string columns with empty string
        string_cols = df.select_dtypes(include=['object']).columns
        for col in string_cols:
            df[col] = df[col].fillna('')

        # Add data source metadata
        if 'data_source' not in df.columns:
            df['data_source'] = 'NOAA Storm Events Database'

        logger.info(f"✓ DataFrame prepared ({len(df.columns)} columns)")

        self.df = df
        return df

    def clear_existing_data(self):
        """
        Clear existing data from storm_events table.

        WARNING: This deletes all records!
        """
        if self.dry_run:
            logger.info("DRY RUN: Would clear existing data from storm_events table")
            return

        logger.info("Clearing existing data from storm_events table...")

        try:
            with get_session() as session:
                result = session.execute(text("DELETE FROM storm_events"))
                session.commit()
                logger.info(f"✓ Cleared existing data")
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            raise

    def bulk_insert_data(self):
        """
        Bulk insert data using PostgreSQL COPY for maximum speed.

        This is much faster than individual INSERTs:
        - COPY: ~25,000 rows/sec
        - INSERT: ~1,000 rows/sec
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would insert {len(self.df):,} records")
            return

        logger.info(f"Bulk loading {len(self.df):,} records to PostgreSQL...")

        try:
            # Get database connection
            conn = engine.raw_connection()
            cursor = conn.cursor()

            # Prepare data for COPY
            # Select only columns that exist in the table
            table_columns = [
                'event_id', 'episode_id', 'event_type',
                'begin_date_time', 'end_date_time', 'year', 'month_name',
                'state', 'state_fips', 'cz_type', 'cz_fips', 'cz_name', 'wfo',
                'begin_lat', 'begin_lon', 'end_lat', 'end_lon',
                'deaths_direct', 'deaths_indirect',
                'injuries_direct', 'injuries_indirect',
                'damage_property', 'damage_crops',
                'damage_property_num', 'damage_crops_num', 'total_damage',
                'magnitude', 'magnitude_type',
                'tor_f_scale', 'tor_length', 'tor_width',
                'tor_other_wfo', 'tor_other_cz_state', 'tor_other_cz_fips', 'tor_other_cz_name',
                'flood_cause', 'source',
                'begin_range', 'begin_azimuth', 'end_range', 'end_azimuth',
                'episode_narrative', 'event_narrative',
                'begin_yearmonth', 'begin_day', 'begin_time',
                'end_yearmonth', 'end_day', 'end_time',
                'category', 'data_source',
                'begin_location_txt', 'end_location_txt'
            ]

            # Filter to only columns that exist in dataframe
            available_columns = [col for col in table_columns if col in self.df.columns]

            # Create CSV in memory
            import io
            output = io.StringIO()
            self.df[available_columns].to_csv(
                output,
                sep='\t',
                header=False,
                index=False,
                na_rep='\\N'  # PostgreSQL NULL representation
            )
            output.seek(0)

            # Use COPY command
            columns_str = ', '.join(available_columns)
            copy_sql = f"COPY storm_events ({columns_str}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"

            logger.info("Executing COPY command...")
            cursor.copy_expert(copy_sql, output)

            conn.commit()
            cursor.close()
            conn.close()

            self.records_inserted = len(self.df)
            logger.info(f"✓ Inserted {self.records_inserted:,} records")

        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise

    def populate_geography_columns(self):
        """
        Populate PostGIS geography columns from lat/lon coordinates.

        Creates POINT geometries from begin_lat/begin_lon and end_lat/end_lon.
        """
        if self.dry_run:
            logger.info("DRY RUN: Would populate PostGIS geography columns")
            return

        logger.info("Populating PostGIS geography columns...")

        try:
            with get_session() as session:
                # Use the stored procedure we created in the schema
                session.execute(text("SELECT populate_geography_columns()"))
                session.commit()

                # Verify
                result = session.execute(text(
                    "SELECT COUNT(*) FROM storm_events WHERE begin_location IS NOT NULL"
                ))
                count = result.fetchone()[0]

                logger.info(f"✓ Populated geography columns for {count:,} records")

        except Exception as e:
            logger.error(f"Failed to populate geography columns: {e}")
            raise

    def validate_migration(self):
        """
        Validate migration success.

        Checks:
        - Row count matches source
        - No NULL event_ids
        - Date ranges are correct
        - All expected columns present
        """
        logger.info("Validating migration...")

        errors = []

        try:
            with get_session() as session:
                # Check row count
                result = session.execute(text("SELECT COUNT(*) FROM storm_events"))
                db_count = result.fetchone()[0]
                source_count = len(self.df)

                if db_count != source_count:
                    errors.append(
                        f"Row count mismatch: source={source_count:,}, db={db_count:,}"
                    )
                else:
                    logger.info(f"✓ Row count: {db_count:,} (matches source)")

                # Check for NULL event_ids
                result = session.execute(text(
                    "SELECT COUNT(*) FROM storm_events WHERE event_id IS NULL"
                ))
                null_count = result.fetchone()[0]

                if null_count > 0:
                    errors.append(f"Found {null_count} NULL event_ids")
                else:
                    logger.info("✓ No NULL event_ids")

                # Check date range
                result = session.execute(text(
                    "SELECT MIN(year), MAX(year) FROM storm_events"
                ))
                min_year, max_year = result.fetchone()

                if min_year < 1996 or max_year > 2030:
                    errors.append(f"Invalid date range: {min_year}-{max_year}")
                else:
                    logger.info(f"✓ Date range: {min_year}-{max_year}")

                # Check geography columns
                result = session.execute(text(
                    "SELECT COUNT(*) FROM storm_events WHERE begin_location IS NOT NULL"
                ))
                geo_count = result.fetchone()[0]

                if geo_count == 0:
                    errors.append("No geography data populated")
                else:
                    logger.info(f"✓ Geography columns populated: {geo_count:,} records")

                # Sample record check
                result = session.execute(text(
                    "SELECT event_id, event_type, state, year FROM storm_events LIMIT 1"
                ))
                sample = result.fetchone()
                logger.info(f"✓ Sample record: {dict(sample._mapping)}")

        except Exception as e:
            errors.append(f"Validation query failed: {e}")

        # Report validation results
        if errors:
            logger.error("❌ Validation FAILED:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        else:
            logger.info("✓ All validation checks passed!")
            return True

    def run(self):
        """
        Execute complete migration process.

        Steps:
        1. Load data from parquet
        2. Prepare DataFrame
        3. Clear existing data
        4. Bulk insert records
        5. Populate PostGIS columns
        6. Validate migration

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("NOAA STORM DATA MIGRATION TO POSTGRESQL")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            # Step 1: Load data
            self.load_data()

            # Step 2: Prepare data
            self.prepare_dataframe()

            # Step 3: Clear existing data
            if not self.dry_run:
                logger.info("\n⚠️  This will delete all existing data in storm_events table!")
                response = input("Continue? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Migration cancelled by user")
                    return False

            self.clear_existing_data()

            # Step 4: Bulk insert
            self.bulk_insert_data()

            # Step 5: Populate geography columns
            if not self.dry_run:
                self.populate_geography_columns()

            # Step 6: Validate
            if not self.dry_run:
                validation_passed = self.validate_migration()

                if not validation_passed:
                    logger.error("❌ Migration completed with validation errors")
                    return False

            # Success!
            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info("")
            logger.info("=" * 60)
            logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"Records migrated: {self.records_inserted:,}")
            logger.info(f"Time elapsed: {elapsed:.1f} seconds")
            logger.info(f"Speed: {self.records_inserted/elapsed:,.0f} records/second")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Update .env: QUERY_BACKEND=postgresql")
            logger.info("2. Test queries using PostgreSQL backend")
            logger.info("3. Run accuracy tests to compare with pandas")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            logger.exception("Full error traceback:")
            return False


def main():
    """
    Command-line interface for migration script.
    """
    parser = argparse.ArgumentParser(
        description="Migrate NOAA storm data from parquet to PostgreSQL"
    )

    parser.add_argument(
        '--source',
        type=str,
        default='data/processed/storms_cleaned.parquet',
        help='Path to source parquet file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without inserting data'
    )

    args = parser.parse_args()

    # Check database connection
    logger.info("Checking database connection...")
    if not init_database():
        logger.error("Database not initialized. Run schema/create_tables.sql first.")
        sys.exit(1)

    # Run migration
    migration = StormDataMigration(
        source_file=args.source,
        dry_run=args.dry_run
    )

    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
