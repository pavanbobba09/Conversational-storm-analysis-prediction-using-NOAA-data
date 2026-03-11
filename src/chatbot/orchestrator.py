"""
Chatbot Orchestrator Module
Connects NLP pipeline → Geocoder → Predictor for end-to-end query processing
"""
import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from nlp.geocoder import Geocoder
from nlp.query_parser import QueryParser
from nlp.entity_resolver import EntityResolver
from models.predictor import StormPredictor


class ChatbotOrchestrator:
    """
    End-to-end chatbot pipeline for storm prediction queries
    """

    def __init__(
        self,
        model_path: str,
        geocoding_file: str,
        historical_data_path: str
    ):
        """
        Initialize chatbot with all required components

        Args:
            model_path: Path to trained prediction model
            geocoding_file: Path to geocoding database (JSON)
            historical_data_path: Path to historical features data
        """
        logger.info("Initializing Storm Forecasting Chatbot...")

        # Initialize NLP components
        logger.info("Loading NLP components...")
        self.geocoder = Geocoder(cities_file=geocoding_file)
        self.parser = QueryParser()
        self.resolver = EntityResolver(self.geocoder, self.parser)

        # Initialize prediction model
        logger.info("Loading prediction model...")
        self.predictor = StormPredictor(model_path, historical_data_path)

        logger.info("Chatbot initialization complete!\n")

    def process_query(self, query: str) -> Dict:
        """
        Process user query end-to-end

        Args:
            query: Natural language query (e.g., "Will there be a storm in Atlanta on August 18, 2028?")

        Returns:
            Dictionary with prediction results and metadata
        """
        logger.info(f"Processing query: '{query}'")

        # Step 1: Resolve entities (location + date)
        resolved = self.resolver.resolve_query(query)

        # Check if query could be fully resolved
        if not resolved['valid']:
            error_msg = self._generate_error_message(resolved)
            return {
                'success': False,
                'error': error_msg,
                'query': query,
                'resolved': resolved
            }

        # Step 2: Make prediction
        try:
            prediction = self.predictor.predict(
                lat=resolved['lat'],
                lon=resolved['lon'],
                date=resolved['date']
            )

            # Step 3: Combine results
            result = {
                'success': True,
                'query': query,
                'location_name': resolved['location_name'],
                'coordinates': (resolved['lat'], resolved['lon']),
                'date': resolved['date'].strftime('%Y-%m-%d'),
                'probability': prediction['probability'],
                'risk_level': prediction['risk_level'],
                'season': prediction['season'],
                'prediction': prediction,
                'resolved': resolved
            }

            logger.info(f"Prediction: {prediction['probability']:.1%} ({prediction['risk_level']} risk)")

            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'success': False,
                'error': f"Prediction failed: {str(e)}",
                'query': query,
                'resolved': resolved
            }

    def _generate_error_message(self, resolved: Dict) -> str:
        """
        Generate helpful error message when query cannot be resolved

        Args:
            resolved: Resolution result from EntityResolver

        Returns:
            Error message string
        """
        if not resolved['coordinates']:
            return (
                f"I couldn't find the location '{resolved['location_name']}'. "
                "Please try a different city or provide more details (e.g., 'Atlanta, GA')."
            )
        elif not resolved['date']:
            return (
                f"I couldn't understand the date '{resolved['date_str']}'. "
                "Please try a format like 'August 18, 2028' or '2028-08-18'."
            )
        else:
            return "I couldn't process your query. Please try rephrasing it."

    def chat(self):
        """
        Interactive chat loop for testing
        """
        logger.info("=== STORM FORECASTING CHATBOT ===")
        logger.info("Ask questions like: 'Will there be a storm in Atlanta on August 18, 2028?'")
        logger.info("Type 'quit' to exit\n")

        while True:
            try:
                query = input("\nYou: ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    logger.info("Goodbye!")
                    break

                result = self.process_query(query)

                if result['success']:
                    # Format response
                    print(f"\nBot: Based on historical patterns, there is a "
                          f"{result['probability']:.1%} chance of storm activity in "
                          f"{result['location_name']} on {result['date']}. "
                          f"This represents a {result['risk_level'].lower()} risk period.")

                    # Add seasonal context
                    season = result['season']
                    if result['risk_level'] == 'High':
                        print(f"     {season} is typically a peak storm season in this area.")
                    elif result['risk_level'] == 'Low':
                        print(f"     {season} is typically a calmer period for this region.")

                else:
                    print(f"\nBot: {result['error']}")

            except KeyboardInterrupt:
                logger.info("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\nBot: Sorry, I encountered an error: {e}")


def main():
    """
    Test chatbot orchestrator
    """
    # Paths
    model_path = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/models/storm_predictor_v1.pkl"
    geocoding_file = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/geocoding/us_cities.json"
    historical_data_path = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed/storms_features.parquet"

    # Check files exist
    for path, name in [(model_path, "Model"), (geocoding_file, "Geocoding"), (historical_data_path, "Historical data")]:
        if not Path(path).exists():
            logger.error(f"{name} file not found: {path}")
            return

    # Initialize chatbot
    chatbot = ChatbotOrchestrator(
        model_path=model_path,
        geocoding_file=geocoding_file,
        historical_data_path=historical_data_path
    )

    # Test with example queries
    test_queries = [
        "Will there be a storm in Atlanta on August 18, 2028?",
        "Storm forecast for Miami next summer",
        "Hurricane risk in New Orleans on 09-15-2028?",
        "Tornado in Oklahoma City on May 15, 2028",
    ]

    logger.info("=== TESTING CHATBOT ORCHESTRATOR ===\n")

    for query in test_queries:
        print("=" * 80)
        result = chatbot.process_query(query)

        if result['success']:
            print(f"✓ Query: {query}")
            print(f"  Location: {result['location_name']} ({result['coordinates'][0]:.2f}, {result['coordinates'][1]:.2f})")
            print(f"  Date: {result['date']} ({result['season']})")
            print(f"  Prediction: {result['probability']:.1%} ({result['risk_level']} risk)")
        else:
            print(f"✗ Query: {query}")
            print(f"  Error: {result['error']}")

        print()

    # Optional: Start interactive chat
    # chatbot.chat()


if __name__ == "__main__":
    main()
