"""
Table Formatter for Gradio Display

Formats DataFrames for display in Gradio UI:
- Selects relevant columns based on query type
- Formats dates and numbers for readability
- Limits rows for performance
- Sorts by relevance

NOTE: This is ONLY for display. Excel export contains full unmodified data.
"""

import pandas as pd
from typing import Dict, List


class TableFormatter:
    """Format DataFrames for Gradio UI display"""

    # Column presets for different query types
    COLUMN_PRESETS = {
        'location_summary': [
            'location', 'event_count', 'total_deaths',
            'total_injuries', 'total_damage'
        ],
        'event_list_deaths': [
            'EVENT_ID', 'EVENT_TYPE', 'STATE', 'CZ_NAME',
            'BEGIN_DATE_TIME', 'DEATHS_DIRECT', 'DEATHS_INDIRECT',
            'INJURIES_DIRECT', 'INJURIES_INDIRECT', 'DAMAGE_PROPERTY'
        ],
        'event_list_damage': [
            'EVENT_ID', 'EVENT_TYPE', 'STATE', 'CZ_NAME',
            'BEGIN_DATE_TIME', 'DAMAGE_PROPERTY', 'DAMAGE_CROPS',
            'TOTAL_DAMAGE'
        ],
        'event_list_default': [
            'EVENT_ID', 'EVENT_TYPE', 'STATE', 'CZ_NAME',
            'BEGIN_DATE_TIME', 'MAGNITUDE', 'DAMAGE_PROPERTY'
        ]
    }

    def format_for_display(self, df: pd.DataFrame, parsed_query: Dict,
                           aggregated: pd.DataFrame = None,
                           max_rows: int = 100) -> pd.DataFrame:
        """
        Format DataFrame for Gradio display

        Args:
            df: Filtered DataFrame from query engine
            parsed_query: Parsed query information
            aggregated: Aggregated location data (if applicable)
            max_rows: Maximum rows to display

        Returns:
            Formatted DataFrame ready for Gradio
        """
        # If we have aggregated location data, use that
        if aggregated is not None and len(aggregated) > 0:
            return self._format_location_table(aggregated, max_rows)

        # Otherwise, format event list
        return self._format_event_table(df, parsed_query, max_rows)

    def _format_location_table(self, df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
        """Format location aggregation table"""
        # Select relevant columns
        display_df = df[self.COLUMN_PRESETS['location_summary']].copy()

        # Rename for better display
        display_df = display_df.rename(columns={
            'location': 'Location',
            'event_count': 'Event Count',
            'total_deaths': 'Deaths',
            'total_injuries': 'Injuries',
            'total_damage': 'Total Damage ($)'
        })

        # Format numbers
        if 'Total Damage ($)' in display_df.columns:
            display_df['Total Damage ($)'] = display_df['Total Damage ($)'].apply(
                lambda x: f"${x:,.0f}" if pd.notnull(x) else "$0"
            )

        # Limit rows
        if len(display_df) > max_rows:
            display_df = display_df.head(max_rows)

        return display_df

    def _format_event_table(self, df: pd.DataFrame, parsed_query: Dict,
                           max_rows: int) -> pd.DataFrame:
        """Format event list table"""
        if len(df) == 0:
            return pd.DataFrame()

        # Determine which columns to show
        preset = self._select_column_preset(parsed_query, df)
        columns = [col for col in preset if col in df.columns]

        # Select columns
        display_df = df[columns].copy()

        # Format date columns
        if 'BEGIN_DATE_TIME' in display_df.columns:
            display_df['BEGIN_DATE_TIME'] = pd.to_datetime(
                display_df['BEGIN_DATE_TIME']
            ).dt.strftime('%Y-%m-%d %H:%M')

        # Format damage columns (for display only - NOT changing data)
        if 'DAMAGE_PROPERTY' in display_df.columns:
            display_df['DAMAGE_PROPERTY'] = display_df['DAMAGE_PROPERTY'].apply(
                self._format_damage_display
            )

        if 'DAMAGE_CROPS' in display_df.columns:
            display_df['DAMAGE_CROPS'] = display_df['DAMAGE_CROPS'].apply(
                self._format_damage_display
            )

        if 'TOTAL_DAMAGE' in display_df.columns:
            display_df['TOTAL_DAMAGE'] = display_df['TOTAL_DAMAGE'].apply(
                lambda x: f"${x:,.0f}" if pd.notnull(x) and x > 0 else "$0"
            )

        # Sort by relevance
        display_df = self._sort_by_relevance(display_df, parsed_query)

        # Limit rows
        if len(display_df) > max_rows:
            display_df = display_df.head(max_rows)

        # Rename columns for better display
        display_df = display_df.rename(columns={
            'EVENT_ID': 'Event ID',
            'EVENT_TYPE': 'Type',
            'STATE': 'State',
            'CZ_NAME': 'County',
            'BEGIN_DATE_TIME': 'Date',
            'DEATHS_DIRECT': 'Deaths (Direct)',
            'DEATHS_INDIRECT': 'Deaths (Indirect)',
            'INJURIES_DIRECT': 'Injuries (Direct)',
            'INJURIES_INDIRECT': 'Injuries (Indirect)',
            'DAMAGE_PROPERTY': 'Property Damage',
            'DAMAGE_CROPS': 'Crop Damage',
            'TOTAL_DAMAGE': 'Total Damage',
            'MAGNITUDE': 'Magnitude'
        })

        return display_df

    def _select_column_preset(self, parsed_query: Dict, df: pd.DataFrame) -> List[str]:
        """Select appropriate column preset based on query"""
        filters = parsed_query.get('filters', {})

        # If querying about deaths, show death columns
        if filters.get('has_deaths'):
            return self.COLUMN_PRESETS['event_list_deaths']

        # If querying about damage, show damage columns
        if filters.get('has_damage'):
            return self.COLUMN_PRESETS['event_list_damage']

        # Default columns
        return self.COLUMN_PRESETS['event_list_default']

    def _format_damage_display(self, value) -> str:
        """Format damage value for display"""
        if pd.isnull(value) or value == '':
            return "$0"
        if isinstance(value, (int, float)):
            if value == 0:
                return "$0"
            return f"${value:,.0f}"
        return str(value)  # Keep original string format (e.g., "5.0K")

    def _sort_by_relevance(self, df: pd.DataFrame, parsed_query: Dict) -> pd.DataFrame:
        """Sort DataFrame by relevance to query"""
        filters = parsed_query.get('filters', {})

        # Sort by deaths if querying about deaths
        if filters.get('has_deaths') and 'DEATHS_DIRECT' in df.columns:
            return df.sort_values('DEATHS_DIRECT', ascending=False)

        # Sort by damage if querying about damage
        if filters.get('has_damage') and 'TOTAL_DAMAGE' in df.columns:
            return df.sort_values('TOTAL_DAMAGE', ascending=False)

        # Default: sort by date (most recent first)
        if 'BEGIN_DATE_TIME' in df.columns:
            return df.sort_values('BEGIN_DATE_TIME', ascending=False)

        return df


# Example usage
if __name__ == "__main__":
    print("Table formatter created successfully!")
    print("This module formats DataFrames for Gradio display.")
