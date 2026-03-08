"""
Data Cleaner Module
Cleans and validates NOAA Storm Events data
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path
from loguru import logger
from typing import Tuple


class StormDataCleaner:
    """
    Cleans NOAA Storm Events data
    """

    def __init__(self):
        logger.info("Initialized StormDataCleaner")

    @staticmethod
    def parse_damage_value(damage_str) -> float:
        """
        Parse damage string (e.g., "10K", "5.0M") to numeric value

        Args:
            damage_str: Damage value as string (e.g., "10.5K", "2.5M", "1.0B")

        Returns:
            Numeric damage value (e.g., 10500.0, 2500000.0, 1000000000.0)
        """
        if pd.isna(damage_str) or damage_str == '':
            return 0.0

        # Convert to string and strip whitespace
        damage_str = str(damage_str).strip().upper()

        # Handle already numeric values
        try:
            return float(damage_str)
        except ValueError:
            pass

        # Parse K (thousands), M (millions), B (billions)
        multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9}

        # Extract numeric part and multiplier
        match = re.match(r'([0-9.]+)\s*([KMB])?', damage_str)
        if match:
            numeric_part = float(match.group(1))
            multiplier_char = match.group(2)

            if multiplier_char in multipliers:
                return numeric_part * multipliers[multiplier_char]
            else:
                return numeric_part

        # If parsing fails, return 0
        logger.warning(f"Could not parse damage value: {damage_str}, returning 0")
        return 0.0

    def parse_damage_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse DAMAGE_PROPERTY and DAMAGE_CROPS columns

        Args:
            df: DataFrame with damage columns

        Returns:
            DataFrame with parsed damage values
        """
        logger.info("Parsing damage columns...")

        if 'DAMAGE_PROPERTY' in df.columns:
            df['DAMAGE_PROPERTY_NUM'] = df['DAMAGE_PROPERTY'].apply(self.parse_damage_value)
            logger.info(f"Parsed DAMAGE_PROPERTY: ${df['DAMAGE_PROPERTY_NUM'].sum():,.0f} total")

        if 'DAMAGE_CROPS' in df.columns:
            df['DAMAGE_CROPS_NUM'] = df['DAMAGE_CROPS'].apply(self.parse_damage_value)
            logger.info(f"Parsed DAMAGE_CROPS: ${df['DAMAGE_CROPS_NUM'].sum():,.0f} total")

        # Create total damage column
        df['TOTAL_DAMAGE'] = df.get('DAMAGE_PROPERTY_NUM', 0) + df.get('DAMAGE_CROPS_NUM', 0)

        return df

    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """
        Validate latitude and longitude values for US storms

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            True if coordinates are valid, False otherwise
        """
        # US bounds (approximately)
        # Latitude: 24.5°N (Florida Keys) to 49.4°N (northern border)
        # Longitude: -125°W (west coast) to -66.9°W (east coast)
        # Extended slightly for Alaska, Hawaii, Puerto Rico

        if pd.isna(lat) or pd.isna(lon):
            return False

        # Check for (0, 0) - invalid placeholder
        if lat == 0 and lon == 0:
            return False

        # Valid ranges (extended for US territories)
        valid_lat = 15.0 <= lat <= 72.0  # Includes Alaska, Hawaii, Puerto Rico
        valid_lon = -180.0 <= lon <= -60.0

        return valid_lat and valid_lon

    def clean_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate coordinate columns

        Args:
            df: DataFrame with BEGIN_LAT and BEGIN_LON columns

        Returns:
            DataFrame with validated coordinates
        """
        logger.info("Cleaning coordinate data...")

        initial_count = len(df)

        # Convert to numeric, coercing errors to NaN
        if 'BEGIN_LAT' in df.columns:
            df['BEGIN_LAT'] = pd.to_numeric(df['BEGIN_LAT'], errors='coerce')

        if 'BEGIN_LON' in df.columns:
            df['BEGIN_LON'] = pd.to_numeric(df['BEGIN_LON'], errors='coerce')

        # Validate coordinates
        if 'BEGIN_LAT' in df.columns and 'BEGIN_LON' in df.columns:
            valid_coords = df.apply(
                lambda row: self.validate_coordinates(row['BEGIN_LAT'], row['BEGIN_LON']),
                axis=1
            )
            df = df[valid_coords].copy()

            removed_count = initial_count - len(df)
            logger.info(f"Removed {removed_count:,} records with invalid coordinates ({removed_count/initial_count*100:.1f}%)")
            logger.info(f"Remaining records: {len(df):,}")

        return df

    def parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse date columns to datetime objects

        Args:
            df: DataFrame with date columns

        Returns:
            DataFrame with parsed dates
        """
        logger.info("Parsing date columns...")

        date_columns = ['BEGIN_DATE_TIME', 'END_DATE_TIME']

        for col in date_columns:
            if col in df.columns:
                # Parse to datetime
                df[col] = pd.to_datetime(df[col], errors='coerce')

                # Log parsing results
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    logger.warning(f"{col}: {null_count:,} dates could not be parsed")

        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing values in key columns

        Args:
            df: DataFrame with potential missing values

        Returns:
            DataFrame with handled missing values
        """
        logger.info("Handling missing values...")

        # Fill numeric columns with 0
        numeric_fill_cols = [
            'INJURIES_DIRECT', 'INJURIES_INDIRECT',
            'DEATHS_DIRECT', 'DEATHS_INDIRECT',
            'DAMAGE_PROPERTY_NUM', 'DAMAGE_CROPS_NUM', 'TOTAL_DAMAGE'
        ]

        for col in numeric_fill_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # Fill MAGNITUDE with median per EVENT_TYPE
        if 'MAGNITUDE' in df.columns and 'EVENT_TYPE' in df.columns:
            df['MAGNITUDE'] = df.groupby('EVENT_TYPE')['MAGNITUDE'].transform(
                lambda x: x.fillna(x.median())
            )

        # Log missing value summary
        missing_summary = df.isnull().sum()
        missing_summary = missing_summary[missing_summary > 0].sort_values(ascending=False)

        if len(missing_summary) > 0:
            logger.info("Remaining missing values:")
            for col, count in missing_summary.head(10).items():
                logger.info(f"  {col}: {count:,} ({count/len(df)*100:.1f}%)")

        return df

    def clean_all(self, df: pd.DataFrame, drop_invalid_coords: bool = True) -> pd.DataFrame:
        """
        Apply all cleaning steps

        Args:
            df: Raw DataFrame
            drop_invalid_coords: Whether to drop records with invalid coordinates

        Returns:
            Cleaned DataFrame
        """
        logger.info(f"Starting data cleaning pipeline on {len(df):,} records...")

        # Step 1: Parse dates
        df = self.parse_dates(df)

        # Step 2: Clean coordinates
        if drop_invalid_coords:
            df = self.clean_coordinates(df)

        # Step 3: Parse damage values
        df = self.parse_damage_columns(df)

        # Step 4: Handle missing values
        df = self.handle_missing_values(df)

        logger.info(f"Data cleaning complete. Final record count: {len(df):,}")

        return df

    def get_cleaning_report(self, original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> dict:
        """
        Generate a report comparing original and cleaned data

        Args:
            original_df: Original DataFrame before cleaning
            cleaned_df: Cleaned DataFrame

        Returns:
            Dictionary with cleaning statistics
        """
        report = {
            'original_records': len(original_df),
            'cleaned_records': len(cleaned_df),
            'records_removed': len(original_df) - len(cleaned_df),
            'removal_percentage': (len(original_df) - len(cleaned_df)) / len(original_df) * 100,
            'total_damage': cleaned_df['TOTAL_DAMAGE'].sum() if 'TOTAL_DAMAGE' in cleaned_df.columns else 0,
            'total_deaths': (
                cleaned_df.get('DEATHS_DIRECT', pd.Series([0])).sum() +
                cleaned_df.get('DEATHS_INDIRECT', pd.Series([0])).sum()
            ),
            'total_injuries': (
                cleaned_df.get('INJURIES_DIRECT', pd.Series([0])).sum() +
                cleaned_df.get('INJURIES_INDIRECT', pd.Series([0])).sum()
            )
        }

        return report


def main():
    """
    Example usage: Clean loaded storm data
    """
    from loader import StormDataLoader

    # Load data
    dataset_dir = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/dataset"
    loader = StormDataLoader(dataset_dir)
    df_raw = loader.load_all_csvs()

    # Clean data
    cleaner = StormDataCleaner()
    df_cleaned = cleaner.clean_all(df_raw.copy())

    # Generate report
    report = cleaner.get_cleaning_report(df_raw, df_cleaned)

    logger.info("\n=== CLEANING REPORT ===")
    logger.info(f"Original Records: {report['original_records']:,}")
    logger.info(f"Cleaned Records: {report['cleaned_records']:,}")
    logger.info(f"Records Removed: {report['records_removed']:,} ({report['removal_percentage']:.2f}%)")
    logger.info(f"Total Damage: ${report['total_damage']:,.0f}")
    logger.info(f"Total Deaths: {report['total_deaths']:,.0f}")
    logger.info(f"Total Injuries: {report['total_injuries']:,.0f}")

    # Save cleaned data
    output_path = Path(dataset_dir).parent / "data" / "processed" / "storms_cleaned.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_cleaned.to_parquet(output_path, index=False)
    logger.info(f"\nSaved cleaned data to: {output_path}")

    return df_cleaned


if __name__ == "__main__":
    main()
