"""
Query Parser for Analytics Chatbot

Parses natural language queries to extract:
- Event types (tornado, hurricane, flood, etc.)
- Locations (states, counties)
- Time periods (years, date ranges)
- Metrics filters (deaths, injuries, damage)
- Output intent (locations vs events list)
"""

import re
from typing import Dict, List, Optional
from datetime import datetime


class AnalyticsQueryParser:
    """Parse natural language queries into structured filters"""

    # Event type mappings: user terms → NOAA EVENT_TYPE values
    EVENT_TYPE_MAPPINGS = {
        'tornado': ['Tornado', 'Funnel Cloud', 'Waterspout'],
        'tornadoes': ['Tornado', 'Funnel Cloud', 'Waterspout'],
        'hurricane': ['Hurricane', 'Hurricane (Typhoon)', 'Tropical Storm'],
        'hurricanes': ['Hurricane', 'Hurricane (Typhoon)', 'Tropical Storm'],
        'flood': ['Flood', 'Flash Flood'],
        'flooding': ['Flood', 'Flash Flood'],
        'floods': ['Flood', 'Flash Flood'],
        'wind': ['Thunderstorm Wind', 'Marine Thunderstorm Wind',
                 'Marine High Wind', 'Marine Strong Wind'],
        'wind-related': ['Thunderstorm Wind', 'Tornado', 'Marine Thunderstorm Wind',
                        'Marine High Wind', 'Marine Strong Wind'],
        'hail': ['Hail', 'Marine Hail'],
        'thunderstorm': ['Thunderstorm Wind', 'Marine Thunderstorm Wind'],
        'lightning': ['Lightning', 'Marine Lightning'],
    }

    # US state name to code mapping (common variations)
    STATE_MAPPINGS = {
        'texas': 'TEXAS',
        'florida': 'FLORIDA',
        'oklahoma': 'OKLAHOMA',
        'kansas': 'KANSAS',
        'louisiana': 'LOUISIANA',
        'mississippi': 'MISSISSIPPI',
        'alabama': 'ALABAMA',
        'georgia': 'GEORGIA',
        'california': 'CALIFORNIA',
        'new york': 'NEW YORK',
        'illinois': 'ILLINOIS',
        # Add more as needed
    }

    def __init__(self):
        """Initialize query parser"""
        pass

    def parse(self, query: str) -> Dict:
        """
        Parse natural language query into structured filters

        Args:
            query: Natural language query string

        Returns:
            Dictionary with parsed query components
        """
        query_lower = query.lower()

        # Extract components
        event_types = self._extract_event_types(query_lower)
        states = self._extract_states(query_lower)
        years = self._extract_years(query_lower)
        has_deaths = self._check_metric(query_lower, 'deaths')
        has_injuries = self._check_metric(query_lower, 'injuries')
        has_damage = self._check_metric(query_lower, 'damage')
        output_mode, group_by = self._detect_output_mode(query_lower)
        query_type = self._classify_query_type(output_mode, has_deaths, has_injuries, has_damage)

        return {
            'raw_query': query,
            'query_type': query_type,
            'filters': {
                'event_types': event_types,
                'states': states,
                'years': years,
                'has_deaths': has_deaths,
                'has_injuries': has_injuries,
                'has_damage': has_damage,
            },
            'output_mode': output_mode,
            'group_by': group_by
        }

    def _extract_event_types(self, query: str) -> Optional[List[str]]:
        """Extract event types from query"""
        for user_term, noaa_types in self.EVENT_TYPE_MAPPINGS.items():
            # Check for exact word match (with word boundaries)
            if re.search(r'\b' + re.escape(user_term) + r'\b', query):
                return noaa_types
        return None

    def _extract_states(self, query: str) -> Optional[List[str]]:
        """Extract state names from query"""
        states = []
        for state_name, state_code in self.STATE_MAPPINGS.items():
            if state_name in query:
                states.append(state_code)

        return states if states else None

    def _extract_years(self, query: str) -> Optional[List[int]]:
        """Extract years from query"""
        years = []

        # Pattern 1: "last X years"
        match = re.search(r'last\s+(\d+)\s+years?', query)
        if match:
            num_years = int(match.group(1))
            current_year = 2025  # Dataset goes up to 2025
            years = list(range(current_year - num_years + 1, current_year + 1))
            return years

        # Pattern 2: "in YYYY"
        match = re.search(r'in\s+(\d{4})', query)
        if match:
            year = int(match.group(1))
            return [year]

        # Pattern 3: "between YYYY and YYYY"
        match = re.search(r'between\s+(\d{4})\s+and\s+(\d{4})', query)
        if match:
            start_year = int(match.group(1))
            end_year = int(match.group(2))
            return list(range(start_year, end_year + 1))

        # Pattern 4: Just a year mentioned (e.g., "2020")
        matches = re.findall(r'\b(20\d{2})\b', query)
        if matches:
            return [int(y) for y in matches]

        return None

    def _check_metric(self, query: str, metric: str) -> bool:
        """Check if metric filter is mentioned in query"""
        metric_patterns = {
            'deaths': [r'\bdeath', r'\bfatalit', r'\bkilled\b', r'\bdied\b'],
            'injuries': [r'\binjur', r'\bhurt\b', r'\bwounded\b'],
            'damage': [r'\bdamage', r'\bdestruction\b', r'\bloss']
        }

        if metric in metric_patterns:
            patterns = metric_patterns[metric]
            for pattern in patterns:
                if re.search(pattern, query):
                    return True

        return False

    def _detect_output_mode(self, query: str) -> tuple:
        """
        Detect output mode and grouping

        Returns:
            (output_mode, group_by)
            output_mode: 'locations' or 'events_list'
            group_by: 'state', 'county', or None
        """
        # Check for location-focused queries
        if 'all locations where' in query or 'where did' in query:
            return ('locations', 'state')

        if 'all places where' in query:
            return ('locations', 'county')

        # Default: return events list
        return ('events_list', None)

    def _classify_query_type(self, output_mode: str, has_deaths: bool,
                            has_injuries: bool, has_damage: bool) -> str:
        """Classify the type of query"""
        if output_mode == 'locations':
            return 'location_query'
        elif has_deaths or has_injuries or has_damage:
            return 'filtered_search'
        else:
            return 'event_list'


# Example usage and testing
if __name__ == "__main__":
    parser = AnalyticsQueryParser()

    # Test queries
    test_queries = [
        "Show me all locations where tornadoes occurred in the last 5 years",
        "Show me all places where hurricane deaths occurred in 2020",
        "Show me events where flooding occurred in Texas in 2020",
        "Give me a list of all wind-related events in the last 10 years",
        "Show me all wind-related events with deaths and property damage in 2020",
    ]

    print("Testing Query Parser:\n")
    for query in test_queries:
        print(f"Query: {query}")
        result = parser.parse(query)
        print(f"  Event Types: {result['filters']['event_types']}")
        print(f"  States: {result['filters']['states']}")
        print(f"  Years: {result['filters']['years']}")
        print(f"  Has Deaths: {result['filters']['has_deaths']}")
        print(f"  Output Mode: {result['output_mode']} (group_by: {result['group_by']})")
        print(f"  Query Type: {result['query_type']}")
        print()
