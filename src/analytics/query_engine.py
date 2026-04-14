"""
Query Engine for Storm Analytics

Executes parsed queries against NOAA storm data:
- Filters data based on parsed criteria
- Aggregates results (location summaries, event lists)
- Calculates summary statistics

Supports both pandas (default) and Polars (experimental) backends.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import os

# Optional Polars support
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None


class StormQueryEngine:
    """Execute analytical queries against NOAA storm data"""

    def __init__(self, data_path: Optional[str] = None, use_cache: bool = True, use_polars: bool = False):
        """
        Initialize query engine with storm data

        Args:
            data_path: Path to parquet file (if None and use_cache=True, uses cache manager)
            use_cache: If True and data_path is None, use pickle cache for 3x faster loading
            use_polars: If True, use Polars for faster queries (experimental)
        """
        # Check environment variable for Polars override
        env_use_polars = os.getenv('USE_POLARS', '').lower() in ('true', '1', 'yes')
        self.use_polars = use_polars or env_use_polars

        if self.use_polars and not POLARS_AVAILABLE:
            print("[WARN] Polars not installed - falling back to pandas")
            self.use_polars = False

        if use_cache and data_path is None:
            # Use cache manager for intelligent caching (pickle → parquet → CSV)
            from src.data.cache_manager import StormDataCacheManager
            print(f"Loading NOAA storm data from cache (backend: {'Polars' if self.use_polars else 'pandas'})...")
            cache_manager = StormDataCacheManager()
            self.df = cache_manager.load_data()
            print(f"[OK] Loaded {len(self.df):,} storm events from cache")
        else:
            # Legacy: direct parquet load
            print(f"Loading NOAA storm data from {data_path} (backend: {'Polars' if self.use_polars else 'pandas'})...")
            self.df = pd.read_parquet(data_path)
            print(f"Loaded {len(self.df):,} storm events")

        # IMPORTANT: Convert datetime BEFORE Polars conversion
        if isinstance(self.df, pd.DataFrame) and 'BEGIN_DATE_TIME' in self.df.columns:
            print("Converting BEGIN_DATE_TIME to datetime format...")
            self.df['BEGIN_DATE_TIME'] = pd.to_datetime(self.df['BEGIN_DATE_TIME'])

        # Convert to Polars if requested (for pandas-loaded data)
        if self.use_polars and isinstance(self.df, pd.DataFrame):
            print("Converting to Polars DataFrame for faster queries...")
            self.df_polars = pl.from_pandas(self.df)
            # Keep pandas version for compatibility
            self.df_pandas = self.df
        else:
            self.df_polars = None
            self.df_pandas = self.df

    def execute_query(self, parsed_query: Dict) -> Dict:
        """
        Execute parsed query and return results

        Args:
            parsed_query: Output from AnalyticsQueryParser.parse()

        Returns:
            Dictionary with filtered data and summary statistics
        """
        filters = parsed_query['filters']
        output_mode = parsed_query['output_mode']
        group_by = parsed_query['group_by']

        # Apply filters
        filtered_df = self.apply_filters(filters)

        # Check if we have results
        if len(filtered_df) == 0:
            return {
                'success': True,
                'data': filtered_df,
                'summary': {
                    'total_events': 0,
                    'date_range': (None, None),
                    'states_covered': [],
                    'total_deaths': 0,
                    'total_injuries': 0,
                    'total_damage': 0.0
                },
                'aggregated': None
            }

        # Generate summary statistics
        summary = self._calculate_summary(filtered_df)

        # Aggregate by location if requested
        aggregated = None
        if output_mode == 'locations' and group_by:
            aggregated = self._aggregate_by_location(filtered_df, group_by)

        return {
            'success': True,
            'data': filtered_df,
            'summary': summary,
            'aggregated': aggregated
        }

    def apply_filters(self, filters: Dict) -> pd.DataFrame:
        """
        Apply filters to DataFrame using Polars (if enabled) or pandas

        Args:
            filters: Dictionary of filter criteria

        Returns:
            Filtered pandas DataFrame (converted from Polars if necessary)
        """
        import time

        backend = "Polars" if (self.use_polars and self.df_polars is not None) else "Pandas"
        print(f"      [ENGINE] Using {backend} backend for filtering...")

        start = time.time()
        if self.use_polars and self.df_polars is not None:
            result = self._apply_filters_polars(filters)
        else:
            result = self._apply_filters_pandas(filters)

        elapsed = time.time() - start
        print(f"      [PERF] Filtered 1.9M records -> {len(result):,} results in {elapsed:.3f}s using {backend}")

        return result

    def _apply_filters_pandas(self, filters: Dict) -> pd.DataFrame:
        """Apply filters using pandas (original implementation)"""
        df = self.df.copy()

        # Event type filter
        if filters.get('event_types'):
            df = df[df['EVENT_TYPE'].isin(filters['event_types'])]

        # State filter
        if filters.get('states'):
            df = df[df['STATE'].isin(filters['states'])]

        # Year filter
        if filters.get('years'):
            df = df[df['YEAR'].isin(filters['years'])]

        # Deaths filter
        if filters.get('has_deaths'):
            df = df[(df['DEATHS_DIRECT'] > 0) | (df['DEATHS_INDIRECT'] > 0)]

        # Injuries filter
        if filters.get('has_injuries'):
            df = df[(df['INJURIES_DIRECT'] > 0) | (df['INJURIES_INDIRECT'] > 0)]

        # Damage filter
        if filters.get('has_damage'):
            df = df[df['TOTAL_DAMAGE'] > 0]

        return df

    def _apply_filters_polars(self, filters: Dict) -> pd.DataFrame:
        """Apply filters using Polars for 5-10x faster queries"""
        df_lazy = self.df_polars

        # Event type filter
        if filters.get('event_types'):
            df_lazy = df_lazy.filter(pl.col('EVENT_TYPE').is_in(filters['event_types']))

        # State filter
        if filters.get('states'):
            df_lazy = df_lazy.filter(pl.col('STATE').is_in(filters['states']))

        # Year filter
        if filters.get('years'):
            df_lazy = df_lazy.filter(pl.col('YEAR').is_in(filters['years']))

        # Deaths filter
        if filters.get('has_deaths'):
            df_lazy = df_lazy.filter(
                (pl.col('DEATHS_DIRECT').fill_null(0) > 0) |
                (pl.col('DEATHS_INDIRECT').fill_null(0) > 0)
            )

        # Injuries filter
        if filters.get('has_injuries'):
            df_lazy = df_lazy.filter(
                (pl.col('INJURIES_DIRECT').fill_null(0) > 0) |
                (pl.col('INJURIES_INDIRECT').fill_null(0) > 0)
            )

        # Damage filter
        if filters.get('has_damage'):
            df_lazy = df_lazy.filter(pl.col('TOTAL_DAMAGE').fill_null(0) > 0)

        # Convert back to pandas for compatibility with downstream code
        return df_lazy.to_pandas()

    def _calculate_summary(self, df: pd.DataFrame) -> Dict:
        """Calculate summary statistics for result set"""
        # Get date range
        if 'BEGIN_DATE_TIME' in df.columns and len(df) > 0:
            date_range = (
                df['BEGIN_DATE_TIME'].min().strftime('%Y-%m-%d'),
                df['BEGIN_DATE_TIME'].max().strftime('%Y-%m-%d')
            )
        else:
            date_range = (None, None)

        # Calculate totals
        total_deaths = (
            df['DEATHS_DIRECT'].fillna(0).sum() +
            df['DEATHS_INDIRECT'].fillna(0).sum()
        )

        total_injuries = (
            df['INJURIES_DIRECT'].fillna(0).sum() +
            df['INJURIES_INDIRECT'].fillna(0).sum()
        )

        total_damage = df['TOTAL_DAMAGE'].fillna(0).sum()

        # Get unique states
        states_covered = sorted(df['STATE'].unique().tolist()) if 'STATE' in df.columns else []

        return {
            'total_events': len(df),
            'date_range': date_range,
            'states_covered': states_covered,
            'total_deaths': int(total_deaths),
            'total_injuries': int(total_injuries),
            'total_damage': float(total_damage)
        }

    def _aggregate_by_location(self, df: pd.DataFrame, group_by: str) -> pd.DataFrame:
        """
        Aggregate events by location

        Args:
            df: Filtered DataFrame
            group_by: 'state' or 'county'

        Returns:
            Aggregated DataFrame with location statistics
        """
        if group_by == 'state':
            group_col = 'STATE'
        elif group_by == 'county':
            group_col = ['STATE', 'CZ_NAME']
        else:
            return None

        # Group and aggregate
        agg_dict = {
            'EVENT_ID': 'count',
            'DEATHS_DIRECT': 'sum',
            'DEATHS_INDIRECT': 'sum',
            'INJURIES_DIRECT': 'sum',
            'INJURIES_INDIRECT': 'sum',
            'TOTAL_DAMAGE': 'sum',
        }

        aggregated = df.groupby(group_col).agg(agg_dict).reset_index()

        # Rename columns
        aggregated = aggregated.rename(columns={
            'EVENT_ID': 'event_count'
        })

        # Calculate total deaths/injuries
        aggregated['total_deaths'] = (
            aggregated['DEATHS_DIRECT'].fillna(0) +
            aggregated['DEATHS_INDIRECT'].fillna(0)
        ).astype(int)

        aggregated['total_injuries'] = (
            aggregated['INJURIES_DIRECT'].fillna(0) +
            aggregated['INJURIES_INDIRECT'].fillna(0)
        ).astype(int)

        # Format location name
        if group_by == 'state':
            aggregated['location'] = aggregated['STATE']
        else:
            aggregated['location'] = aggregated['CZ_NAME'] + ', ' + aggregated['STATE']

        # Select and order columns
        result_cols = ['location', 'event_count', 'total_deaths', 'total_injuries', 'TOTAL_DAMAGE']
        aggregated = aggregated[result_cols].copy()
        aggregated = aggregated.rename(columns={'TOTAL_DAMAGE': 'total_damage'})

        # Sort by event count (descending)
        aggregated = aggregated.sort_values('event_count', ascending=False)

        return aggregated


# Example usage and testing
if __name__ == "__main__":
    import sys
    sys.path.append('/Users/pavanbobba/Documents/master\'s_Project/Conversational-storm-analysis-prediction-using-NOAA-data')

    from src.analytics.query_parser import AnalyticsQueryParser

    # Initialize
    data_path = '/Users/pavanbobba/Documents/master\'s_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed/storms_cleaned.parquet'
    parser = AnalyticsQueryParser()
    engine = StormQueryEngine(data_path)

    # Test query
    query = "Show me all locations where tornadoes occurred in the last 5 years"
    print(f"\nTest Query: {query}\n")

    parsed = parser.parse(query)
    results = engine.execute_query(parsed)

    print(f"Total Events: {results['summary']['total_events']:,}")
    print(f"Date Range: {results['summary']['date_range']}")
    print(f"States: {len(results['summary']['states_covered'])} states")
    print(f"Total Deaths: {results['summary']['total_deaths']:,}")
    print(f"Total Damage: ${results['summary']['total_damage']:,.0f}")

    if results['aggregated'] is not None:
        print(f"\nTop 10 locations:")
        print(results['aggregated'].head(10))
