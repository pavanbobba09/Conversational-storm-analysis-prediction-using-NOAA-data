"""
Query Engine for Storm Analytics

Executes parsed queries against NOAA storm data:
- Filters data based on parsed criteria
- Aggregates results (location summaries, event lists)
- Calculates summary statistics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path


class StormQueryEngine:
    """Execute analytical queries against NOAA storm data"""

    def __init__(self, data_path: str):
        """
        Initialize query engine with storm data

        Args:
            data_path: Path to storms_cleaned.parquet file
        """
        print(f"Loading NOAA storm data from {data_path}...")
        self.df = pd.read_parquet(data_path)
        print(f"Loaded {len(self.df):,} storm events")

        # Ensure datetime type
        if 'BEGIN_DATE_TIME' in self.df.columns:
            self.df['BEGIN_DATE_TIME'] = pd.to_datetime(self.df['BEGIN_DATE_TIME'])

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
        Apply filters to DataFrame

        Args:
            filters: Dictionary of filter criteria

        Returns:
            Filtered DataFrame
        """
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
