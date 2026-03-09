"""
Geocoding Service Module
Maps city/location names to geographic coordinates (lat/lon)
"""
import pandas as pd
import json
from pathlib import Path
from loguru import logger
from typing import Dict, Optional, Tuple
from difflib import get_close_matches


class Geocoder:
    """
    Geocoding service that converts location names to coordinates
    """

    def __init__(self, cities_file: Optional[str] = None):
        """
        Initialize geocoder

        Args:
            cities_file: Path to JSON file with city-to-coords mapping
        """
        self.cities_file = cities_file
        self.city_lookup = {}

        if cities_file and Path(cities_file).exists():
            self.load_cities(cities_file)
            logger.info(f"Loaded {len(self.city_lookup)} cities from {cities_file}")
        else:
            logger.info("Geocoder initialized without pre-loaded cities")

    def build_from_noaa_data(self, df: pd.DataFrame) -> Dict:
        """
        Build city-to-coordinates lookup from NOAA storm data

        Args:
            df: DataFrame with storm data (must have CZ_NAME, STATE, BEGIN_LAT, BEGIN_LON)

        Returns:
            Dictionary mapping location names to coordinates
        """
        logger.info("Building geocoding database from NOAA data...")

        # Filter to valid rows with coordinates
        valid_data = df[
            (df['CZ_NAME'].notna()) &
            (df['STATE'].notna()) &
            (df['BEGIN_LAT'].notna()) &
            (df['BEGIN_LON'].notna())
        ].copy()

        logger.info(f"Processing {len(valid_data):,} valid location records...")

        # Group by location and calculate average coordinates
        location_groups = valid_data.groupby(['CZ_NAME', 'STATE']).agg({
            'BEGIN_LAT': 'mean',
            'BEGIN_LON': 'mean'
        }).reset_index()

        # Build lookup dictionary
        city_lookup = {}

        for _, row in location_groups.iterrows():
            location_name = row['CZ_NAME']
            state = row['STATE']
            lat = round(row['BEGIN_LAT'], 4)
            lon = round(row['BEGIN_LON'], 4)

            # Create multiple lookup keys for flexibility
            # 1. Full name with state (e.g., "Harris County, TX")
            full_key = f"{location_name}, {state}"
            city_lookup[full_key.lower()] = {
                'lat': lat,
                'lon': lon,
                'name': location_name,
                'state': state
            }

            # 2. Just the location name (e.g., "Harris County")
            # Only add if not already present (to avoid overwriting with different state)
            if location_name.lower() not in city_lookup:
                city_lookup[location_name.lower()] = {
                    'lat': lat,
                    'lon': lon,
                    'name': location_name,
                    'state': state
                }

            # 3. If it's a county, also add without "County" suffix
            if 'county' in location_name.lower():
                short_name = location_name.replace(' County', '').replace(' county', '')
                short_key = f"{short_name}, {state}"
                city_lookup[short_key.lower()] = {
                    'lat': lat,
                    'lon': lon,
                    'name': location_name,
                    'state': state
                }

        logger.info(f"Created {len(city_lookup):,} location lookup entries")
        logger.info(f"Covering {len(location_groups):,} unique locations across {df['STATE'].nunique()} states")

        self.city_lookup = city_lookup
        return city_lookup

    def geocode(self, location: str, fuzzy: bool = True, threshold: float = 0.6) -> Optional[Dict]:
        """
        Convert location name to coordinates

        Args:
            location: Location name (e.g., "Atlanta", "Harris County, TX")
            fuzzy: Whether to use fuzzy matching for misspellings
            threshold: Minimum similarity score for fuzzy matches (0-1)

        Returns:
            Dictionary with lat, lon, name, state or None if not found
        """
        if not location:
            return None

        location_lower = location.lower().strip()

        # Try exact match first
        if location_lower in self.city_lookup:
            return self.city_lookup[location_lower]

        # Try fuzzy matching
        if fuzzy:
            matches = get_close_matches(
                location_lower,
                self.city_lookup.keys(),
                n=1,
                cutoff=threshold
            )
            if matches:
                matched_key = matches[0]
                logger.info(f"Fuzzy matched '{location}' to '{matched_key}'")
                return self.city_lookup[matched_key]

        # Not found
        logger.warning(f"Location '{location}' not found in geocoding database")
        return None

    def geocode_to_coords(self, location: str) -> Optional[Tuple[float, float]]:
        """
        Get just the coordinates (lat, lon) for a location

        Args:
            location: Location name

        Returns:
            Tuple of (lat, lon) or None if not found
        """
        result = self.geocode(location)
        if result:
            return (result['lat'], result['lon'])
        return None

    def save_cities(self, output_path: str):
        """
        Save city lookup to JSON file

        Args:
            output_path: Path to save JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.city_lookup, f, indent=2)

        logger.info(f"Saved {len(self.city_lookup)} cities to {output_path}")

    def load_cities(self, cities_file: str):
        """
        Load city lookup from JSON file

        Args:
            cities_file: Path to JSON file
        """
        with open(cities_file, 'r') as f:
            self.city_lookup = json.load(f)

        logger.info(f"Loaded {len(self.city_lookup)} cities from {cities_file}")

    def get_stats(self) -> Dict:
        """
        Get statistics about the geocoding database

        Returns:
            Dictionary with stats
        """
        if not self.city_lookup:
            return {'total_locations': 0}

        states = set()
        for loc_data in self.city_lookup.values():
            states.add(loc_data['state'])

        return {
            'total_locations': len(self.city_lookup),
            'unique_states': len(states),
            'states': sorted(list(states))
        }


def main():
    """
    Build geocoding database from NOAA data
    """
    # Load cleaned NOAA data
    data_path = Path("/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed/storms_cleaned.parquet")

    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        logger.info("Please run data cleaning pipeline first")
        return

    logger.info(f"Loading cleaned data from: {data_path}")
    df = pd.read_parquet(data_path)

    # Initialize geocoder
    geocoder = Geocoder()

    # Build lookup from NOAA data
    geocoder.build_from_noaa_data(df)

    # Save to JSON
    output_path = Path("/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/geocoding/us_cities.json")
    geocoder.save_cities(output_path)

    # Test with some examples
    logger.info("\n=== TESTING GEOCODER ===")

    test_locations = [
        "Harris County, TX",
        "Atlanta",
        "Miami",
        "Los Angeles County",
        "New York",
        "Atlnta",  # Misspelling
        "Unknown City"
    ]

    for location in test_locations:
        result = geocoder.geocode(location)
        if result:
            logger.info(f"✓ {location:20s} → {result['name']}, {result['state']} ({result['lat']:.2f}, {result['lon']:.2f})")
        else:
            logger.info(f"✗ {location:20s} → NOT FOUND")

    # Print stats
    stats = geocoder.get_stats()
    logger.info(f"\n=== GEOCODING DATABASE STATS ===")
    logger.info(f"Total locations: {stats['total_locations']:,}")
    logger.info(f"Unique states: {stats['unique_states']}")

    return geocoder


if __name__ == "__main__":
    main()
