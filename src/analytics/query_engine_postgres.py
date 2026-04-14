"""
PostgreSQL Query Engine for Storm Analytics

Executes parsed queries against NOAA storm data using PostgreSQL:
- Uses SQLAlchemy for database queries
- Returns pandas DataFrames for compatibility with existing code
- Identical interface to StormQueryEngine (pandas version)
"""

import pandas as pd
from typing import Dict, List, Optional
from sqlalchemy import text, func, or_
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_session, engine
from src.database.models import StormEvent


class PostgreSQLQueryEngine:
    """Execute analytical queries against NOAA storm data in PostgreSQL"""

    def __init__(self):
        """Initialize PostgreSQL query engine"""
        print("📡 Connecting to PostgreSQL database...")

        # Test connection
        with get_session() as session:
            # Get record count
            result = session.execute(text("SELECT COUNT(*) FROM storm_events"))
            count = result.fetchone()[0]

            # Get year range
            result = session.execute(text("SELECT MIN(year), MAX(year) FROM storm_events"))
            min_year, max_year = result.fetchone()

            # Get event type count
            result = session.execute(text("SELECT COUNT(DISTINCT event_type) FROM storm_events"))
            event_types = result.fetchone()[0]

            print(f"✅ Connected to PostgreSQL Database:")
            print(f"   └─ Total Records: {count:,}")
            print(f"   └─ Year Range: {min_year}-{max_year}")
            print(f"   └─ Event Types: {event_types}")
            print(f"   └─ Database: noaa_storms")
            print(f"   └─ Backend: PostgreSQL 17 + PostGIS 3.6")

    def execute_query(self, parsed_query: Dict) -> Dict:
        """
        Execute parsed query and return results

        Args:
            parsed_query: Output from AnalyticsQueryParser.parse()
                - filters: Dict with event_types, states, years, etc.
                - output_mode: 'locations' or 'events_list'
                - group_by: 'state' or 'county' (for locations mode)

        Returns:
            Dictionary with filtered data and summary statistics:
            {
                'success': True,
                'data': pd.DataFrame,      # All matching events
                'summary': {               # Summary statistics
                    'total_events': int,
                    'date_range': (str, str),
                    'states_covered': List[str],
                    'total_deaths': int,
                    'total_injuries': int,
                    'total_damage': float
                },
                'aggregated': pd.DataFrame | None  # Location aggregation
            }
        """
        filters = parsed_query['filters']
        output_mode = parsed_query['output_mode']
        group_by = parsed_query['group_by']

        # Log query details
        print()
        print("🔍 PostgreSQL Query Execution:")
        print("-" * 70)
        if filters.get('event_types'):
            print(f"   Event Types: {', '.join(filters['event_types'])}")
        if filters.get('states'):
            print(f"   States: {', '.join(filters['states'])}")
        if filters.get('years'):
            print(f"   Years: {', '.join(map(str, filters['years']))}")
        if filters.get('has_deaths'):
            print(f"   Filter: Events with deaths")
        if filters.get('has_injuries'):
            print(f"   Filter: Events with injuries")
        if filters.get('has_damage'):
            print(f"   Filter: Events with damage")
        print(f"   Output Mode: {output_mode}")
        if group_by:
            print(f"   Group By: {group_by}")
        print("-" * 70)

        with get_session() as session:
            # Build and execute SQL query
            filtered_df = self.apply_filters(session, filters)

            print(f"✅ Query Result: {len(filtered_df):,} events found")
            print("-" * 70)

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
                aggregated = self._aggregate_by_location(session, filters, group_by)

            return {
                'success': True,
                'data': filtered_df,
                'summary': summary,
                'aggregated': aggregated
            }

    def apply_filters(self, session: Session, filters: Dict) -> pd.DataFrame:
        """
        Apply filters to database query using SQLAlchemy

        Args:
            session: SQLAlchemy session
            filters: Dictionary of filter criteria

        Returns:
            Filtered DataFrame (pandas)
        """
        # Build SQL query
        sql_parts = ["SELECT * FROM storm_events WHERE 1=1"]
        params = {}

        # Event type filter
        if filters.get('event_types'):
            event_types = filters['event_types']
            placeholders = ', '.join([f":event_type_{i}" for i in range(len(event_types))])
            sql_parts.append(f"AND event_type IN ({placeholders})")
            for i, event_type in enumerate(event_types):
                params[f'event_type_{i}'] = event_type

        # State filter (case-insensitive matching)
        if filters.get('states'):
            states = filters['states']
            placeholders = ', '.join([f":state_{i}" for i in range(len(states))])
            sql_parts.append(f"AND UPPER(state) IN ({placeholders})")
            for i, state in enumerate(states):
                params[f'state_{i}'] = state.upper()

        # Year filter
        if filters.get('years'):
            years = filters['years']
            placeholders = ', '.join([f":year_{i}" for i in range(len(years))])
            sql_parts.append(f"AND year IN ({placeholders})")
            for i, year in enumerate(years):
                params[f'year_{i}'] = year

        # Deaths filter
        if filters.get('has_deaths'):
            sql_parts.append("AND (deaths_direct > 0 OR deaths_indirect > 0)")

        # Injuries filter
        if filters.get('has_injuries'):
            sql_parts.append("AND (injuries_direct > 0 OR injuries_indirect > 0)")

        # Damage filter
        if filters.get('has_damage'):
            sql_parts.append("AND total_damage > 0")

        # Combine SQL query
        sql_query = " ".join(sql_parts)

        # Execute query and convert to DataFrame
        df = pd.read_sql(text(sql_query), session.connection(), params=params)

        # Ensure column names are uppercase (match pandas version)
        df.columns = df.columns.str.upper()

        return df

    def _calculate_summary(self, df: pd.DataFrame) -> Dict:
        """
        Calculate summary statistics for result set

        Args:
            df: Filtered DataFrame

        Returns:
            Dictionary with summary statistics
        """
        # Get date range
        if 'BEGIN_DATE_TIME' in df.columns and len(df) > 0:
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(df['BEGIN_DATE_TIME']):
                df['BEGIN_DATE_TIME'] = pd.to_datetime(df['BEGIN_DATE_TIME'])

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

    def _aggregate_by_location(self, session: Session, filters: Dict, group_by: str) -> pd.DataFrame:
        """
        Aggregate events by location using SQL GROUP BY

        Args:
            session: SQLAlchemy session
            filters: Filter criteria (to be reapplied)
            group_by: 'state' or 'county'

        Returns:
            Aggregated DataFrame with location statistics
        """
        if group_by == 'state':
            group_col = 'state'
            select_cols = """
                state,
                state as location
            """
        elif group_by == 'county':
            group_col = 'state, cz_name'
            select_cols = """
                state,
                cz_name,
                cz_name || ', ' || state as location
            """
        else:
            return None

        # Build SQL query with filters
        sql_parts = [f"""
            SELECT
                {select_cols},
                COUNT(*) as event_count,
                SUM(deaths_direct) as deaths_direct,
                SUM(deaths_indirect) as deaths_indirect,
                SUM(injuries_direct) as injuries_direct,
                SUM(injuries_indirect) as injuries_indirect,
                SUM(total_damage) as total_damage
            FROM storm_events
            WHERE 1=1
        """]
        params = {}

        # Apply same filters as main query
        if filters.get('event_types'):
            event_types = filters['event_types']
            placeholders = ', '.join([f":event_type_{i}" for i in range(len(event_types))])
            sql_parts.append(f"AND event_type IN ({placeholders})")
            for i, event_type in enumerate(event_types):
                params[f'event_type_{i}'] = event_type

        if filters.get('states'):
            states = filters['states']
            placeholders = ', '.join([f":state_{i}" for i in range(len(states))])
            sql_parts.append(f"AND UPPER(state) IN ({placeholders})")
            for i, state in enumerate(states):
                params[f'state_{i}'] = state.upper()

        if filters.get('years'):
            years = filters['years']
            placeholders = ', '.join([f":year_{i}" for i in range(len(years))])
            sql_parts.append(f"AND year IN ({placeholders})")
            for i, year in enumerate(years):
                params[f'year_{i}'] = year

        if filters.get('has_deaths'):
            sql_parts.append("AND (deaths_direct > 0 OR deaths_indirect > 0)")

        if filters.get('has_injuries'):
            sql_parts.append("AND (injuries_direct > 0 OR injuries_indirect > 0)")

        if filters.get('has_damage'):
            sql_parts.append("AND total_damage > 0")

        # Add GROUP BY and ORDER BY
        sql_parts.append(f"""
            GROUP BY {group_col}
            ORDER BY event_count DESC
        """)

        sql_query = " ".join(sql_parts)

        # Execute and get DataFrame
        aggregated = pd.read_sql(text(sql_query), session.connection(), params=params)

        # Calculate total deaths/injuries
        aggregated['total_deaths'] = (
            aggregated['deaths_direct'].fillna(0) +
            aggregated['deaths_indirect'].fillna(0)
        ).astype(int)

        aggregated['total_injuries'] = (
            aggregated['injuries_direct'].fillna(0) +
            aggregated['injuries_indirect'].fillna(0)
        ).astype(int)

        # Select and order columns (match pandas version)
        result_cols = ['location', 'event_count', 'total_deaths', 'total_injuries', 'total_damage']
        aggregated = aggregated[result_cols].copy()

        return aggregated


# Example usage and testing
if __name__ == "__main__":
    from src.analytics.query_parser_gemini import AnalyticsQueryParser
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize
    parser = AnalyticsQueryParser(api_key=os.getenv('GROQ_API_KEY'))
    engine = PostgreSQLQueryEngine()

    # Test query
    query = "Show me all locations where tornadoes occurred in the last 5 years"
    print(f"\nTest Query: {query}\n")

    parsed = parser.parse(query)
    print(f"Parsed filters: {parsed['filters']}")
    print(f"Output mode: {parsed['output_mode']}")
    print(f"Group by: {parsed['group_by']}\n")

    results = engine.execute_query(parsed)

    print(f"Total Events: {results['summary']['total_events']:,}")
    print(f"Date Range: {results['summary']['date_range']}")
    print(f"States: {len(results['summary']['states_covered'])} states")
    print(f"Total Deaths: {results['summary']['total_deaths']:,}")
    print(f"Total Damage: ${results['summary']['total_damage']:,.0f}")

    if results['aggregated'] is not None:
        print(f"\nTop 10 locations:")
        print(results['aggregated'].head(10))
