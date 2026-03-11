"""
Storm Prediction Module
Loads trained model and makes predictions for new queries
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Dict, Optional, Tuple


class StormPredictor:
    """
    Predicts storm probability for given location and date
    """

    def __init__(self, model_path: str, historical_data_path: str = None):
        """
        Initialize predictor

        Args:
            model_path: Path to trained model package (.pkl file)
            historical_data_path: Optional path to historical features data
        """
        self.model_path = Path(model_path)
        self.model = None
        self.feature_columns = None
        self.is_calibrated = False
        self.historical_lookup = None

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.load_model()

        # Load historical data if provided
        if historical_data_path and Path(historical_data_path).exists():
            self.load_historical_data(historical_data_path)

    def load_model(self):
        """
        Load trained model package
        """
        logger.info(f"Loading model from: {self.model_path}")

        model_package = joblib.load(self.model_path)

        self.model = model_package['model']
        self.feature_columns = model_package['feature_columns']
        self.is_calibrated = model_package.get('is_calibrated', False)

        logger.info(f"Model loaded successfully")
        logger.info(f"  Features: {len(self.feature_columns)}")
        logger.info(f"  Calibrated: {self.is_calibrated}")

    def load_historical_data(self, data_path: str):
        """
        Load historical features for location-based lookup

        Args:
            data_path: Path to historical features parquet file
        """
        logger.info(f"Loading historical data from: {data_path}")

        df = pd.read_parquet(data_path)

        # Create lookup table: (lat_rounded, lon_rounded, month) -> historical features
        lookup = df[['lat_rounded', 'lon_rounded', 'month',
                     'storms_location_month_avg_per_year',
                     'historical_storm_probability',
                     'most_common_event_encoded']].drop_duplicates()

        # Convert to dictionary for fast lookup
        self.historical_lookup = {}
        for _, row in lookup.iterrows():
            key = (row['lat_rounded'], row['lon_rounded'], row['month'])
            self.historical_lookup[key] = {
                'storms_location_month_avg_per_year': row['storms_location_month_avg_per_year'],
                'historical_storm_probability': row['historical_storm_probability'],
                'most_common_event_encoded': row['most_common_event_encoded']
            }

        logger.info(f"Loaded {len(self.historical_lookup):,} historical location-month combinations")

    def _generate_features(self, lat: float, lon: float, date: datetime) -> pd.DataFrame:
        """
        Generate features for prediction

        Args:
            lat: Latitude
            lon: Longitude
            date: Datetime object

        Returns:
            DataFrame with features matching training format
        """
        # Temporal features
        month = date.month
        day_of_year = date.timetuple().tm_yday
        week_of_year = date.isocalendar()[1]
        day_of_week = date.weekday()

        # Season encoding (0=Winter, 1=Spring, 2=Summer, 3=Fall)
        if month in [12, 1, 2]:
            season_encoded = 0
        elif month in [3, 4, 5]:
            season_encoded = 1
        elif month in [6, 7, 8]:
            season_encoded = 2
        else:
            season_encoded = 3

        # Peak season indicators
        is_summer_peak = 1 if month in [6, 7, 8] else 0
        is_tornado_season = 1 if month in [3, 4, 5, 6] else 0
        is_hurricane_season = 1 if month in [6, 7, 8, 9, 10, 11] else 0

        # Cyclic encodings
        month_sin = np.sin(2 * np.pi * month / 12)
        month_cos = np.cos(2 * np.pi * month / 12)
        day_of_year_sin = np.sin(2 * np.pi * day_of_year / 365)
        day_of_year_cos = np.cos(2 * np.pi * day_of_year / 365)

        # Spatial features (round to 0.5° grid)
        lat_rounded = np.round(lat * 2) / 2
        lon_rounded = np.round(lon * 2) / 2

        # Historical features - lookup from historical data
        if self.historical_lookup:
            key = (lat_rounded, lon_rounded, month)
            hist_features = self.historical_lookup.get(key)

            if hist_features:
                storms_location_month_avg_per_year = hist_features['storms_location_month_avg_per_year']
                historical_storm_probability = hist_features['historical_storm_probability']
                most_common_event_encoded = hist_features['most_common_event_encoded']
            else:
                # Location not in historical data - use conservative defaults
                storms_location_month_avg_per_year = 0.1
                historical_storm_probability = 0.1
                most_common_event_encoded = 0
        else:
            # No historical data loaded - use defaults
            storms_location_month_avg_per_year = 0.1
            historical_storm_probability = 0.1
            most_common_event_encoded = 0

        # Create features dictionary
        features = {
            'month': month,
            'day_of_year': day_of_year,
            'week_of_year': week_of_year,
            'day_of_week': day_of_week,
            'season_encoded': season_encoded,
            'is_summer_peak': is_summer_peak,
            'is_tornado_season': is_tornado_season,
            'is_hurricane_season': is_hurricane_season,
            'month_sin': month_sin,
            'month_cos': month_cos,
            'day_of_year_sin': day_of_year_sin,
            'day_of_year_cos': day_of_year_cos,
            'lat_rounded': lat_rounded,
            'lon_rounded': lon_rounded,
            'storms_location_month_avg_per_year': storms_location_month_avg_per_year,
            'historical_storm_probability': historical_storm_probability,
            'most_common_event_encoded': most_common_event_encoded
        }

        # Convert to DataFrame with correct column order
        df = pd.DataFrame([features])
        df = df[self.feature_columns]

        return df

    def predict(self, lat: float, lon: float, date: datetime) -> Dict:
        """
        Predict storm probability

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            date: Datetime object

        Returns:
            Dictionary with prediction results
        """
        # Validate inputs
        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat} (must be -90 to 90)")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon} (must be -180 to 180)")

        logger.info(f"Predicting for: lat={lat:.2f}, lon={lon:.2f}, date={date.strftime('%Y-%m-%d')}")

        # Generate features
        X = self._generate_features(lat, lon, date)

        # Make prediction
        probability = self.model.predict_proba(X)[0, 1]

        # Determine risk level
        if probability < 0.3:
            risk_level = "Low"
        elif probability < 0.6:
            risk_level = "Medium"
        else:
            risk_level = "High"

        result = {
            'probability': float(probability),
            'risk_level': risk_level,
            'location': {'lat': lat, 'lon': lon},
            'date': date.strftime('%Y-%m-%d'),
            'month': date.month,
            'season': ['Winter', 'Spring', 'Summer', 'Fall'][
                0 if date.month in [12, 1, 2] else
                1 if date.month in [3, 4, 5] else
                2 if date.month in [6, 7, 8] else 3
            ]
        }

        logger.info(f"Prediction: {probability:.2%} ({risk_level} risk)")

        return result

    def predict_batch(self, locations: list, dates: list) -> pd.DataFrame:
        """
        Predict storm probabilities for multiple locations/dates

        Args:
            locations: List of (lat, lon) tuples
            dates: List of datetime objects

        Returns:
            DataFrame with predictions
        """
        if len(locations) != len(dates):
            raise ValueError("locations and dates must have same length")

        results = []
        for (lat, lon), date in zip(locations, dates):
            result = self.predict(lat, lon, date)
            results.append(result)

        return pd.DataFrame(results)


def main():
    """
    Test predictor with example queries
    """
    logger.info("=== TESTING STORM PREDICTOR ===\n")

    # Paths
    model_path = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/models/storm_predictor_v1.pkl"
    historical_data_path = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed/storms_features.parquet"

    if not Path(model_path).exists():
        logger.error(f"Model file not found: {model_path}")
        logger.info("Please run trainer.py first to train the model")
        return

    predictor = StormPredictor(model_path, historical_data_path)

    # Test queries
    test_cases = [
        # (lat, lon, date_string, description)
        (33.75, -84.39, "2028-08-18", "Atlanta, August 2028 (summer peak)"),
        (25.76, -80.19, "2028-09-15", "Miami, September 2028 (hurricane season)"),
        (35.47, -97.52, "2028-05-15", "Oklahoma City, May 2028 (tornado season)"),
        (29.95, -90.07, "2028-06-01", "New Orleans, June 2028 (hurricane season start)"),
        (47.61, -122.33, "2028-12-25", "Seattle, December 2028 (winter)"),
        (40.71, -74.01, "2028-03-15", "New York, March 2028 (spring)"),
    ]

    logger.info("Testing predictions:\n")

    for lat, lon, date_str, description in test_cases:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        print("-" * 80)
        print(f"Query: {description}")

        result = predictor.predict(lat, lon, date)

        print(f"  Location: ({result['location']['lat']:.2f}, {result['location']['lon']:.2f})")
        print(f"  Date: {result['date']} ({result['season']})")
        print(f"  Storm Probability: {result['probability']:.1%}")
        print(f"  Risk Level: {result['risk_level']}")
        print()

    logger.info("=== TESTING COMPLETE ===")


if __name__ == "__main__":
    main()
