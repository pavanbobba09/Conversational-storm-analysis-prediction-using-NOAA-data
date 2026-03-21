"""
Entity Resolver Module
Links extracted entities to concrete values (coordinates, dates)
"""
import dateparser
from datetime import datetime
from loguru import logger
from typing import Dict, Optional, Tuple
from pathlib import Path

# Import our custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from nlp.geocoder import Geocoder
from nlp.query_parser import QueryParser


class EntityResolver:
    """
    Resolves extracted entities to usable values for prediction
    """

    def __init__(self, geocoder: Geocoder, parser: QueryParser):
        """
        Initialize entity resolver

        Args:
            geocoder: Geocoding service
            parser: BERT query parser
        """
        self.geocoder = geocoder
        self.parser = parser
        logger.info("EntityResolver initialized")

    def detect_date_type(self, date_str: str) -> str:
        """
        Detect if query contains specific date or just year

        Args:
            date_str: Extracted date string

        Returns:
            'year_only', 'month_year', or 'specific_date'
        """
        import re

        # Year-only patterns: "2029", "2035", "in 2035", "at 2029"
        if re.match(r'^\d{4}$', date_str.strip()):
            return 'year_only'
        if re.match(r'^(?:in|at)\s+20\d{2}$', date_str.strip(), re.IGNORECASE):
            return 'year_only'

        # Month + Year: "August 2029"
        if re.match(r'^[A-Z][a-z]+\s+20\d{2}$', date_str.strip()):
            return 'month_year'

        # Everything else is specific date
        return 'specific_date'

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object

        Args:
            date_str: Date string (e.g., "August 18, 2028", "tomorrow", "next summer")

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            # Use dateparser for flexible parsing
            parsed_date = dateparser.parse(
                date_str,
                settings={
                    'PREFER_DATES_FROM': 'future',  # Assume future dates for predictions
                    'RETURN_AS_TIMEZONE_AWARE': False
                }
            )

            if parsed_date:
                logger.info(f"Parsed date '{date_str}' → {parsed_date.strftime('%Y-%m-%d')}")
                return parsed_date
            else:
                logger.warning(f"Could not parse date: '{date_str}'")
                return None

        except Exception as e:
            logger.error(f"Date parsing error for '{date_str}': {e}")
            return None

    def resolve_location(self, location_str: str) -> Optional[Tuple[float, float]]:
        """
        Resolve location string to coordinates

        Args:
            location_str: Location name (e.g., "Atlanta", "New York")

        Returns:
            Tuple of (lat, lon) or None if not found
        """
        if not location_str:
            return None

        # Use geocoder
        coords = self.geocoder.geocode_to_coords(location_str)

        if coords:
            logger.info(f"Resolved location '{location_str}' → ({coords[0]:.2f}, {coords[1]:.2f})")
            return coords
        else:
            logger.warning(f"Could not resolve location: '{location_str}'")
            return None

    def resolve_query(self, query: str) -> Dict:
        """
        Parse query and resolve all entities

        Args:
            query: User's natural language query

        Returns:
            Dictionary with resolved entities
        """
        logger.info(f"Resolving query: '{query}'")

        # Step 1: Parse query with BERT
        parsed = self.parser.parse(query)

        # Step 2: Resolve location to coordinates
        coords = None
        if parsed['location']:
            coords = self.resolve_location(parsed['location'])

        # Step 3: Parse date to datetime and detect type
        parsed_date = None
        query_type = 'specific_date'  # default
        if parsed['date']:
            query_type = self.detect_date_type(parsed['date'])
            parsed_date = self.parse_date(parsed['date'])

        # Step 4: Build result
        result = {
            'query': query,
            'location_name': parsed['location'],
            'coordinates': coords,
            'lat': coords[0] if coords else None,
            'lon': coords[1] if coords else None,
            'date_str': parsed['date'],
            'date': parsed_date,
            'query_type': query_type,  # NEW: track query type
            'intent': parsed['intent'],
            'valid': coords is not None and parsed_date is not None
        }

        # Add temporal features if date is valid
        if parsed_date:
            result.update({
                'year': parsed_date.year,
                'month': parsed_date.month,
                'day': parsed_date.day,
                'day_of_year': parsed_date.timetuple().tm_yday
            })

        logger.info(f"Resolution result: valid={result['valid']}, "
                   f"location={result['location_name']}, "
                   f"coords={result['coordinates']}, "
                   f"date={result['date']}")

        return result

    def validate_query(self, query: str) -> bool:
        """
        Check if query can be fully resolved

        Args:
            query: User query

        Returns:
            True if query is valid and resolvable
        """
        result = self.resolve_query(query)
        return result['valid']


def main():
    """
    Test entity resolver with end-to-end examples
    """
    logger.info("=== TESTING ENTITY RESOLVER ===\n")

    # Initialize components
    geocoding_file = Path("/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/geocoding/us_cities.json")

    if not geocoding_file.exists():
        logger.error(f"Geocoding file not found: {geocoding_file}")
        logger.info("Please run geocoder.py first to build the database")
        return

    # Load geocoder
    geocoder = Geocoder(cities_file=str(geocoding_file))

    # Load BERT parser
    parser = QueryParser()

    # Initialize resolver
    resolver = EntityResolver(geocoder, parser)

    # Test queries
    test_queries = [
        "Will there be a storm in Atlanta on August 18, 2028?",
        "Storm forecast for Miami next summer",
        "Hurricane risk in New Orleans on 09-15-2028?",
        "Tornado in Oklahoma City on May 15, 2028",
        "Storm in Seattle tomorrow",
        "Invalid query",
    ]

    logger.info("Testing end-to-end resolution:\n")

    for query in test_queries:
        print("-" * 80)
        result = resolver.resolve_query(query)

        print(f"Query: {query}")
        print(f"  Location: {result['location_name']} → ({result['lat']}, {result['lon']})")
        print(f"  Date: {result['date_str']} → {result['date']}")
        if result['date']:
            print(f"    Year: {result['year']}, Month: {result['month']}, Day: {result['day']}")
        print(f"  Valid for prediction: {result['valid']}")
        print()

    logger.info("=== TESTING COMPLETE ===")


if __name__ == "__main__":
    main()
