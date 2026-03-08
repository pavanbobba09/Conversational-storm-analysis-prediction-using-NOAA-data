"""
Feature Engineering Module
Extracts and creates features from cleaned NOAA Storm Events data
"""
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Tuple, Dict
import joblib


class StormFeatureEngineer:
    """
    Feature engineering for storm prediction
    """

    def __init__(self, grid_size: float = 0.5):
        """
        Initialize feature engineer

        Args:
            grid_size: Size of spatial grid cells in degrees (default: 0.5° ≈ 50 miles)
        """
        self.grid_size = grid_size
        logger.info(f"Initialized StormFeatureEngineer with grid_size={grid_size}°")

    def extract_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract temporal features from BEGIN_DATE_TIME

        Args:
            df: DataFrame with BEGIN_DATE_TIME column

        Returns:
            DataFrame with added temporal features
        """
        logger.info("Extracting temporal features...")

        if 'BEGIN_DATE_TIME' not in df.columns:
            raise ValueError("BEGIN_DATE_TIME column not found")

        # Ensure datetime type
        df['BEGIN_DATE_TIME'] = pd.to_datetime(df['BEGIN_DATE_TIME'])

        # Extract basic temporal components
        df['year'] = df['BEGIN_DATE_TIME'].dt.year
        df['month'] = df['BEGIN_DATE_TIME'].dt.month
        df['day'] = df['BEGIN_DATE_TIME'].dt.day
        df['day_of_year'] = df['BEGIN_DATE_TIME'].dt.dayofyear
        df['week_of_year'] = df['BEGIN_DATE_TIME'].dt.isocalendar().week
        df['day_of_week'] = df['BEGIN_DATE_TIME'].dt.dayofweek

        # Season mapping
        def get_season(month):
            if month in [12, 1, 2]:
                return 'Winter'
            elif month in [3, 4, 5]:
                return 'Spring'
            elif month in [6, 7, 8]:
                return 'Summer'
            else:  # 9, 10, 11
                return 'Fall'

        df['season'] = df['month'].apply(get_season)

        # Encode season as numeric for modeling
        season_map = {'Winter': 0, 'Spring': 1, 'Summer': 2, 'Fall': 3}
        df['season_encoded'] = df['season'].map(season_map)

        # Peak season indicators
        df['is_summer_peak'] = (df['month'].isin([6, 7, 8])).astype(int)
        df['is_tornado_season'] = (df['month'].isin([3, 4, 5, 6])).astype(int)
        df['is_hurricane_season'] = (df['month'].isin([6, 7, 8, 9, 10, 11])).astype(int)

        # Cyclic encoding for month (preserves circular nature: Dec -> Jan)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

        # Cyclic encoding for day of year
        df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
        df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365)

        logger.info("Temporal features extracted successfully")
        return df

    def extract_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract spatial features and create grid cells

        Args:
            df: DataFrame with BEGIN_LAT and BEGIN_LON columns

        Returns:
            DataFrame with added spatial features
        """
        logger.info("Extracting spatial features...")

        if 'BEGIN_LAT' not in df.columns or 'BEGIN_LON' not in df.columns:
            raise ValueError("BEGIN_LAT and BEGIN_LON columns required")

        # Round coordinates to grid cells
        df['lat_rounded'] = (df['BEGIN_LAT'] / self.grid_size).round() * self.grid_size
        df['lon_rounded'] = (df['BEGIN_LON'] / self.grid_size).round() * self.grid_size

        # Create grid cell ID
        df['grid_cell_id'] = df['lat_rounded'].astype(str) + '_' + df['lon_rounded'].astype(str)

        # Count unique grid cells
        unique_cells = df['grid_cell_id'].nunique()
        logger.info(f"Created {unique_cells:,} unique spatial grid cells")

        return df

    def calculate_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate historical aggregation features

        Args:
            df: DataFrame with storm events

        Returns:
            DataFrame with historical features
        """
        logger.info("Calculating historical features...")

        # Group by location-month to calculate historical patterns
        location_month_groups = df.groupby(['grid_cell_id', 'month'])

        # Storm frequency per location-month across all years
        logger.info("Calculating storm frequency per location-month...")
        freq_df = location_month_groups.size().reset_index(name='storms_location_month_count')

        # Calculate years of data per location-month
        years_df = location_month_groups['year'].nunique().reset_index(name='years_of_data')
        freq_df = freq_df.merge(years_df, on=['grid_cell_id', 'month'])

        # Average storms per year for this location-month
        freq_df['storms_location_month_avg_per_year'] = freq_df['storms_location_month_count'] / freq_df['years_of_data']

        # Merge back to main dataframe
        df = df.merge(freq_df[['grid_cell_id', 'month', 'storms_location_month_avg_per_year']],
                     on=['grid_cell_id', 'month'],
                     how='left')

        # Historical probability (simple baseline)
        df['historical_storm_probability'] = df['storms_location_month_avg_per_year'] / 30  # Approximate days per month

        # Most common event type per location-month
        logger.info("Finding most common event types per location-month...")
        most_common_event = location_month_groups['EVENT_TYPE'].agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Unknown')
        most_common_event = most_common_event.reset_index(name='most_common_event_type')
        df = df.merge(most_common_event, on=['grid_cell_id', 'month'], how='left')

        # Encode event types
        event_types = df['most_common_event_type'].unique()
        event_type_map = {event: idx for idx, event in enumerate(event_types)}
        df['most_common_event_encoded'] = df['most_common_event_type'].map(event_type_map)

        # Average damage per location-month
        if 'TOTAL_DAMAGE' in df.columns:
            avg_damage = location_month_groups['TOTAL_DAMAGE'].mean().reset_index(name='avg_damage_location_month')
            df = df.merge(avg_damage, on=['grid_cell_id', 'month'], how='left')

        # State-level features
        if 'STATE' in df.columns:
            # Encode state
            states = df['STATE'].unique()
            state_map = {state: idx for idx, state in enumerate(states)}
            df['state_encoded'] = df['STATE'].map(state_map)

            # Storm frequency by state-month
            state_month_freq = df.groupby(['STATE', 'month']).size().reset_index(name='storms_state_month_count')
            df = df.merge(state_month_freq, on=['STATE', 'month'], how='left')

        logger.info("Historical features calculated successfully")
        return df

    def create_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create target variable for modeling

        Args:
            df: DataFrame with storm events

        Returns:
            DataFrame with target variable
        """
        logger.info("Creating target variable...")

        # For each row, target is 1 (storm occurred)
        df['storm_occurred'] = 1

        logger.info("Target variable created (all events are positive cases)")
        logger.info("Note: Negative samples (no-storm days) should be generated separately for training")

        return df

    def generate_negative_samples(self,
                                  df: pd.DataFrame,
                                  ratio: float = 2.0,
                                  random_state: int = 42) -> pd.DataFrame:
        """
        Generate negative samples (no-storm days) for balanced training

        Args:
            df: DataFrame with positive storm events
            ratio: Ratio of negative to positive samples (e.g., 2.0 = 2x negative samples)
            random_state: Random seed for reproducibility

        Returns:
            DataFrame with both positive and negative samples
        """
        logger.info(f"Generating negative samples with ratio={ratio}...")

        np.random.seed(random_state)

        # Get unique grid cells and date range
        grid_cells = df['grid_cell_id'].unique()
        min_date = df['BEGIN_DATE_TIME'].min()
        max_date = df['BEGIN_DATE_TIME'].max()

        # Calculate number of negative samples needed
        n_positive = len(df)
        n_negative = int(n_positive * ratio)

        logger.info(f"Positive samples: {n_positive:,}")
        logger.info(f"Generating {n_negative:,} negative samples...")

        negative_samples = []

        for _ in range(n_negative):
            # Random grid cell
            grid_cell = np.random.choice(grid_cells)

            # Random date
            random_date = min_date + pd.Timedelta(
                days=np.random.randint(0, (max_date - min_date).days + 1)
            )

            # Extract lat/lon from grid_cell_id
            lat_str, lon_str = grid_cell.split('_')
            lat = float(lat_str)
            lon = float(lon_str)

            negative_samples.append({
                'BEGIN_DATE_TIME': random_date,
                'BEGIN_LAT': lat,
                'BEGIN_LON': lon,
                'grid_cell_id': grid_cell,
                'storm_occurred': 0  # Negative sample
            })

        # Create DataFrame from negative samples
        df_negative = pd.DataFrame(negative_samples)

        # Add temporal features to negative samples
        df_negative = self.extract_temporal_features(df_negative)

        # Add spatial features
        df_negative['lat_rounded'] = df_negative['BEGIN_LAT']
        df_negative['lon_rounded'] = df_negative['BEGIN_LON']

        # Merge with historical features from positive samples
        historical_cols = ['grid_cell_id', 'month', 'storms_location_month_avg_per_year',
                          'historical_storm_probability', 'most_common_event_type',
                          'most_common_event_encoded']

        # Get unique historical features
        hist_features = df[historical_cols].drop_duplicates()

        df_negative = df_negative.merge(hist_features, on=['grid_cell_id', 'month'], how='left')

        # Fill NaN for locations with no historical data
        df_negative['storms_location_month_avg_per_year'] = df_negative['storms_location_month_avg_per_year'].fillna(0)
        df_negative['historical_storm_probability'] = df_negative['historical_storm_probability'].fillna(0)
        df_negative['most_common_event_encoded'] = df_negative['most_common_event_encoded'].fillna(-1)

        # Combine positive and negative samples
        logger.info("Combining positive and negative samples...")
        df_combined = pd.concat([df, df_negative], ignore_index=True)

        # Shuffle
        df_combined = df_combined.sample(frac=1, random_state=random_state).reset_index(drop=True)

        logger.info(f"Combined dataset: {len(df_combined):,} total samples")
        logger.info(f"  Positive: {(df_combined['storm_occurred']==1).sum():,} ({(df_combined['storm_occurred']==1).sum()/len(df_combined)*100:.1f}%)")
        logger.info(f"  Negative: {(df_combined['storm_occurred']==0).sum():,} ({(df_combined['storm_occurred']==0).sum()/len(df_combined)*100:.1f}%)")

        return df_combined

    def engineer_all_features(self, df: pd.DataFrame, include_negative_samples: bool = True) -> pd.DataFrame:
        """
        Apply all feature engineering steps

        Args:
            df: Cleaned DataFrame
            include_negative_samples: Whether to generate negative samples

        Returns:
            Feature-engineered DataFrame ready for modeling
        """
        logger.info(f"Starting feature engineering pipeline on {len(df):,} records...")

        # Step 1: Extract temporal features
        df = self.extract_temporal_features(df)

        # Step 2: Extract spatial features
        df = self.extract_spatial_features(df)

        # Step 3: Calculate historical features
        df = self.calculate_historical_features(df)

        # Step 4: Create target variable
        df = self.create_target_variable(df)

        # Step 5: Generate negative samples (optional)
        if include_negative_samples:
            df = self.generate_negative_samples(df, ratio=2.0)

        logger.info(f"Feature engineering complete. Final dataset: {len(df):,} records")

        return df

    def get_feature_list(self, df: pd.DataFrame) -> dict:
        """
        Get list of engineered features by category

        Args:
            df: Feature-engineered DataFrame

        Returns:
            Dictionary of feature lists by category
        """
        features = {
            'temporal': [
                'month', 'day_of_year', 'week_of_year', 'day_of_week',
                'season_encoded', 'is_summer_peak', 'is_tornado_season', 'is_hurricane_season',
                'month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos'
            ],
            'spatial': [
                'lat_rounded', 'lon_rounded', 'BEGIN_LAT', 'BEGIN_LON'
            ],
            'historical': [
                'storms_location_month_avg_per_year', 'historical_storm_probability',
                'most_common_event_encoded'
            ],
            'target': ['storm_occurred']
        }

        # Filter to only include features that exist in dataframe
        features = {
            category: [f for f in feature_list if f in df.columns]
            for category, feature_list in features.items()
        }

        return features

    def save_feature_metadata(self, df: pd.DataFrame, output_path: str):
        """
        Save feature metadata for later use in prediction

        Args:
            df: Feature-engineered DataFrame
            output_path: Path to save metadata
        """
        metadata = {
            'grid_size': self.grid_size,
            'features': self.get_feature_list(df),
            'event_type_mapping': df['most_common_event_type'].unique().tolist() if 'most_common_event_type' in df.columns else [],
            'date_range': {
                'min': str(df['BEGIN_DATE_TIME'].min()),
                'max': str(df['BEGIN_DATE_TIME'].max())
            },
            'grid_cells': df['grid_cell_id'].unique().tolist() if 'grid_cell_id' in df.columns else []
        }

        joblib.dump(metadata, output_path)
        logger.info(f"Saved feature metadata to: {output_path}")


def main():
    """
    Example usage: Engineer features from cleaned data
    """
    # Load cleaned data
    data_dir = Path("/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed")
    cleaned_data_path = data_dir / "storms_cleaned.parquet"

    if not cleaned_data_path.exists():
        logger.error(f"Cleaned data not found at {cleaned_data_path}")
        logger.info("Please run loader.py and cleaner.py first")
        return

    logger.info(f"Loading cleaned data from: {cleaned_data_path}")
    df_cleaned = pd.read_parquet(cleaned_data_path)

    # Initialize feature engineer
    engineer = StormFeatureEngineer(grid_size=0.5)

    # Engineer features
    df_features = engineer.engineer_all_features(df_cleaned, include_negative_samples=True)

    # Get feature list
    features = engineer.get_feature_list(df_features)
    logger.info("\n=== FEATURE SUMMARY ===")
    for category, feature_list in features.items():
        logger.info(f"{category.upper()}: {len(feature_list)} features")
        logger.info(f"  {', '.join(feature_list)}")

    # Save feature-engineered data
    output_path = data_dir / "storms_features.parquet"
    df_features.to_parquet(output_path, index=False)
    logger.info(f"\nSaved feature-engineered data to: {output_path}")

    # Save metadata
    metadata_path = data_dir / "feature_metadata.pkl"
    engineer.save_feature_metadata(df_features, metadata_path)

    return df_features


if __name__ == "__main__":
    main()
