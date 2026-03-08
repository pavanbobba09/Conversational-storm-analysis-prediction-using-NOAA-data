"""
Data Loader Module
Loads and merges NOAA StormEvents CSV files from 2015-2025
"""
import pandas as pd
import glob
import os
from pathlib import Path
from loguru import logger
from tqdm import tqdm


class StormDataLoader:
    """
    Loads NOAA Storm Events data from multiple CSV files
    """

    def __init__(self, dataset_dir: str):
        """
        Initialize the data loader

        Args:
            dataset_dir: Path to directory containing StormEvents CSV files
        """
        self.dataset_dir = Path(dataset_dir)
        if not self.dataset_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

        logger.info(f"Initialized StormDataLoader with dataset dir: {self.dataset_dir}")

    def get_csv_files(self):
        """
        Find all StormEvents CSV files in the dataset directory

        Returns:
            List of CSV file paths sorted by year
        """
        csv_pattern = str(self.dataset_dir / "StormEvents_details-*.csv")
        csv_files = sorted(glob.glob(csv_pattern))

        if not csv_files:
            raise FileNotFoundError(f"No CSV files found matching pattern: {csv_pattern}")

        logger.info(f"Found {len(csv_files)} CSV files")
        return csv_files

    def load_single_csv(self, filepath: str) -> pd.DataFrame:
        """
        Load a single CSV file

        Args:
            filepath: Path to CSV file

        Returns:
            DataFrame with storm data
        """
        try:
            # Read CSV with low_memory=False to avoid dtype warnings
            df = pd.read_csv(filepath, low_memory=False, encoding='utf-8')
            logger.info(f"Loaded {len(df)} records from {Path(filepath).name}")
            return df
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding if utf-8 fails
            logger.warning(f"UTF-8 decode failed for {filepath}, trying latin-1")
            df = pd.read_csv(filepath, low_memory=False, encoding='latin-1')
            logger.info(f"Loaded {len(df)} records from {Path(filepath).name} with latin-1 encoding")
            return df
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            raise

    def load_all_csvs(self) -> pd.DataFrame:
        """
        Load and merge all CSV files into a single DataFrame

        Returns:
            Merged DataFrame containing all storm events
        """
        csv_files = self.get_csv_files()

        logger.info("Loading all CSV files...")
        dataframes = []

        for filepath in tqdm(csv_files, desc="Loading CSVs"):
            df = self.load_single_csv(filepath)
            dataframes.append(df)

        # Concatenate all dataframes
        logger.info("Merging dataframes...")
        merged_df = pd.concat(dataframes, ignore_index=True)

        logger.info(f"Successfully merged {len(merged_df)} total storm events from {len(csv_files)} files")
        logger.info(f"Date range: {merged_df['BEGIN_DATE_TIME'].min()} to {merged_df['BEGIN_DATE_TIME'].max()}")
        logger.info(f"DataFrame shape: {merged_df.shape}")
        logger.info(f"Columns: {list(merged_df.columns)}")

        return merged_df

    def get_data_summary(self, df: pd.DataFrame) -> dict:
        """
        Get summary statistics about the loaded data

        Args:
            df: DataFrame to summarize

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_records': len(df),
            'total_columns': len(df.columns),
            'date_range': {
                'start': str(df['BEGIN_DATE_TIME'].min()),
                'end': str(df['BEGIN_DATE_TIME'].max())
            },
            'unique_states': df['STATE'].nunique() if 'STATE' in df.columns else 0,
            'unique_event_types': df['EVENT_TYPE'].nunique() if 'EVENT_TYPE' in df.columns else 0,
            'missing_values': df.isnull().sum().to_dict(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024)
        }

        return summary


def main():
    """
    Example usage: Load all NOAA storm data
    """
    # Default dataset directory
    dataset_dir = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/dataset"

    # Initialize loader
    loader = StormDataLoader(dataset_dir)

    # Load all data
    df = loader.load_all_csvs()

    # Get summary
    summary = loader.get_data_summary(df)

    logger.info("Data Summary:")
    logger.info(f"Total Records: {summary['total_records']:,}")
    logger.info(f"Total Columns: {summary['total_columns']}")
    logger.info(f"Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    logger.info(f"Unique States: {summary['unique_states']}")
    logger.info(f"Unique Event Types: {summary['unique_event_types']}")
    logger.info(f"Memory Usage: {summary['memory_usage_mb']:.2f} MB")

    # Display top event types
    if 'EVENT_TYPE' in df.columns:
        logger.info("\nTop 10 Event Types:")
        logger.info(df['EVENT_TYPE'].value_counts().head(10))

    # Save to parquet for faster loading later
    output_path = Path(dataset_dir).parent / "data" / "processed" / "storms_raw.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info(f"\nSaved raw merged data to: {output_path}")

    return df


if __name__ == "__main__":
    main()
