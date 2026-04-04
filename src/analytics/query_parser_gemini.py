"""
Groq-Powered Query Parser for Storm Analytics

Uses Groq's LLM API to understand natural language queries and extract:
- Event types (tornado, hurricane, flood, etc.)
- Locations (states, counties)
- Time periods (years, date ranges)
- Metrics filters (deaths, injuries, damage)
- Output intent (locations vs events list)
"""

import json
from groq import Groq
from typing import Dict, Optional
from .config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE


class GroqQueryParser:
    """Parse natural language queries using Groq API"""

    # Available event types in NOAA data
    AVAILABLE_EVENT_TYPES = [
        'Tornado', 'Funnel Cloud', 'Waterspout',
        'Hurricane', 'Hurricane (Typhoon)', 'Tropical Storm',
        'Flood', 'Flash Flood',
        'Thunderstorm Wind', 'Marine Thunderstorm Wind',
        'Marine High Wind', 'Marine Strong Wind',
        'Hail', 'Marine Hail',
        'Lightning', 'Marine Lightning'
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq-powered query parser

        Args:
            api_key: Groq API key (uses config if not provided)
        """
        self.api_key = api_key or GROQ_API_KEY

        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError(
                "Groq API key not configured! "
                "Please set GROQ_API_KEY in your .env file. "
                "Get your key from: https://console.groq.com/"
            )

        # Configure Groq client
        self.client = Groq(api_key=self.api_key)

    def parse(self, query: str) -> Dict:
        """
        Parse natural language query using Groq

        Args:
            query: Natural language query string

        Returns:
            Dictionary with parsed query components
        """
        # Create prompt for Groq
        prompt = self._create_parsing_prompt(query)

        # Call Groq API
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a query parser for a storm analytics system. Extract structured information and return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=GROQ_TEMPERATURE,
        )

        # Parse Groq's response
        try:
            response_text = response.choices[0].message.content
            parsed_data = json.loads(response_text)

            # Add original query
            parsed_data['raw_query'] = query

            # Validate and clean the parsed data
            parsed_data = self._validate_parsed_data(parsed_data)

            return parsed_data

        except json.JSONDecodeError:
            # Fallback: Return basic structure
            return self._create_fallback_response(query)

    def _create_parsing_prompt(self, query: str) -> str:
        """Create prompt for Gemini to extract query components"""
        return f"""You are a query parser for a storm analytics system. Extract structured information from the user's natural language query.

Available storm types: {', '.join(self.AVAILABLE_EVENT_TYPES)}

User Query: "{query}"

Extract the following information and return ONLY a valid JSON object (no markdown, no explanation):

{{
    "query_type": "location_query" or "event_list" or "filtered_search",
    "filters": {{
        "event_types": [list of storm types from available types, or null],
        "states": [list of US state names in UPPERCASE, or null],
        "years": [list of years as integers, or null],
        "has_deaths": true/false,
        "has_injuries": true/false,
        "has_damage": true/false
    }},
    "output_mode": "locations" or "events_list",
    "group_by": "state" or "county" or null
}}

Rules:
1. For "last X years", use years 2021-2025 for "last 5 years" (dataset spans 1996-2025)
2. Map user's storm terms to available types (e.g., "tornadoes" → ["Tornado", "Funnel Cloud", "Waterspout"])
3. State names should be in UPPERCASE (e.g., "TEXAS", "FLORIDA")
4. query_type: "location_query" if asking "where"/"locations", "filtered_search" if has metric filters, else "event_list"
5. output_mode: "locations" if asking about locations/places, else "events_list"
6. group_by: "state" for "locations", "county" for "places", null otherwise
7. Set has_deaths=true if query mentions deaths/fatalities/killed
8. Set has_injuries=true if query mentions injuries/hurt/wounded
9. Set has_damage=true if query mentions damage/destruction

Return ONLY the JSON object, nothing else."""

    def _validate_parsed_data(self, data: Dict) -> Dict:
        """Validate and clean parsed data from Gemini"""
        # Ensure required keys exist
        if 'filters' not in data:
            data['filters'] = {}

        if 'query_type' not in data:
            data['query_type'] = 'event_list'

        if 'output_mode' not in data:
            data['output_mode'] = 'events_list'

        if 'group_by' not in data:
            data['group_by'] = None

        # Ensure booleans are actual booleans
        filters = data['filters']
        filters['has_deaths'] = bool(filters.get('has_deaths', False))
        filters['has_injuries'] = bool(filters.get('has_injuries', False))
        filters['has_damage'] = bool(filters.get('has_damage', False))

        return data

    def _create_fallback_response(self, query: str) -> Dict:
        """Create fallback response if Gemini parsing fails"""
        return {
            'raw_query': query,
            'query_type': 'event_list',
            'filters': {
                'event_types': None,
                'states': None,
                'years': None,
                'has_deaths': False,
                'has_injuries': False,
                'has_damage': False,
            },
            'output_mode': 'events_list',
            'group_by': None,
            'error': 'Failed to parse query with Gemini'
        }


# Example usage and testing
if __name__ == "__main__":
    import sys
    sys.path.append('/Users/pavanbobba/Documents/master\'s_Project/Conversational-storm-analysis-prediction-using-NOAA-data')

    try:
        parser = GeminiQueryParser()

        # Test queries
        test_queries = [
            "Show me all locations where tornadoes occurred in the last 5 years",
            "Show me all places where hurricane deaths occurred in 2020",
            "Show me events where flooding occurred in Texas in 2020",
        ]

        print("Testing Gemini Query Parser:\n")
        for query in test_queries:
            print(f"Query: {query}")
            try:
                result = parser.parse(query)
                print(f"  Event Types: {result['filters']['event_types']}")
                print(f"  States: {result['filters']['states']}")
                print(f"  Years: {result['filters']['years']}")
                print(f"  Has Deaths: {result['filters']['has_deaths']}")
                print(f"  Output Mode: {result['output_mode']} (group_by: {result['group_by']})")
                print(f"  Query Type: {result['query_type']}")
                print()
            except Exception as e:
                print(f"  Error: {e}")
                print()

    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set up your Gemini API key first:")
        print("1. Get key from: https://makersuite.google.com/app/apikey")
        print("2. Create .env file with: GEMINI_API_KEY=your_key_here")
