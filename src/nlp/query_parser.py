"""
BERT Query Parser Module
Extracts location and date entities from natural language queries using BERT NER
"""
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
from loguru import logger
from typing import Dict, List, Optional
import re


class QueryParser:
    """
    BERT-based NER parser for storm prediction queries
    """

    def __init__(self, model_name: str = "dslim/bert-base-NER"):
        """
        Initialize BERT NER parser

        Args:
            model_name: HuggingFace model name (default: BERT NER)
        """
        logger.info(f"Loading BERT NER model: {model_name}")

        try:
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)

            # Create NER pipeline
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple"  # Merge sub-tokens
            )

            logger.info("BERT NER model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            raise

    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text using BERT NER

        Args:
            text: Input text query

        Returns:
            List of entity dictionaries with type, text, score
        """
        if not text:
            return []

        try:
            # Run NER pipeline
            entities = self.ner_pipeline(text)

            # Format results
            formatted_entities = []
            for entity in entities:
                formatted_entities.append({
                    'type': entity['entity_group'],
                    'text': entity['word'].strip(),
                    'score': entity['score']
                })

            return formatted_entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def extract_location(self, text: str) -> Optional[str]:
        """
        Extract location (city/state) from query

        Args:
            text: Input query

        Returns:
            Location string or None
        """
        entities = self.extract_entities(text)

        # Look for GPE (Geo-Political Entity) or LOC (Location)
        for entity in entities:
            if entity['type'] in ['LOC', 'GPE']:
                logger.info(f"Extracted location: '{entity['text']}' (confidence: {entity['score']:.2f})")
                return entity['text']

        # Fallback: Use regex patterns for common location phrases
        location_patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "in Atlanta", "in New York"
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "at Miami"
            r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "near Boston"
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1)
                logger.info(f"Extracted location via regex: '{location}'")
                return location

        logger.warning("No location found in query")
        return None

    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date/time expressions from query

        Args:
            text: Input query

        Returns:
            Date string or None
        """
        # First try BERT NER for DATE entities
        entities = self.extract_entities(text)

        for entity in entities:
            if entity['type'] in ['DATE', 'TIME']:
                logger.info(f"Extracted date via BERT: '{entity['text']}' (confidence: {entity['score']:.2f})")
                return entity['text']

        # Fallback: Regex patterns for common date formats
        date_patterns = [
            # "August 18, 2028", "December 25, 2027"
            r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            # "on August 18"
            r'on\s+([A-Z][a-z]+\s+\d{1,2})',
            # "8/18/2028", "08-18-2028"
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            # "2028-08-18" (ISO format)
            r'(\d{4}-\d{2}-\d{2})',
            # Month + Year: "August 2029", "July 2035"
            r'([A-Z][a-z]+\s+20\d{2})',
            # Year only: "in 2035", "at 2029", "2028"
            r'(?:in|at)\s+(20\d{2})',
            r'\b(20\d{2})\b',
            # Relative: "next summer", "tomorrow", "next week"
            r'(next\s+(?:week|month|year|summer|winter|spring|fall))',
            r'(tomorrow|today)',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                logger.info(f"Extracted date via regex: '{date_str}'")
                return date_str

        logger.warning("No date found in query")
        return None

    def parse(self, query: str) -> Dict:
        """
        Parse query and extract location and date

        Args:
            query: User's natural language query

        Returns:
            Dictionary with extracted information
        """
        logger.info(f"Parsing query: '{query}'")

        # Extract entities
        location = self.extract_location(query)
        date = self.extract_date(query)

        # Determine intent (implicit for now - assume storm prediction)
        intent = "storm_prediction"

        result = {
            'query': query,
            'location': location,
            'date': date,
            'intent': intent,
            'success': location is not None or date is not None
        }

        logger.info(f"Parse result: {result}")
        return result

    def validate_query(self, query: str) -> bool:
        """
        Check if query has required information for prediction

        Args:
            query: User query

        Returns:
            True if query has location and date, False otherwise
        """
        parsed = self.parse(query)
        return parsed['location'] is not None and parsed['date'] is not None


def main():
    """
    Test BERT query parser with example queries
    """
    logger.info("=== TESTING BERT QUERY PARSER ===\n")

    # Initialize parser
    parser = QueryParser()

    # Test queries
    test_queries = [
        "Will there be a storm in Atlanta on August 18, 2028?",
        "Storm forecast for Miami next summer",
        "Is there a hurricane risk in New Orleans on 09-15-2028?",
        "What's the storm probability in Los Angeles December 2027?",
        "Storm in Texas on 2028-08-20",
        "Will it rain in Seattle tomorrow?",
        "Tornado risk Oklahoma City May 15, 2028",
        "Invalid query with no location or date",
    ]

    logger.info("Testing with sample queries:\n")
    for query in test_queries:
        result = parser.parse(query)
        logger.info(f"Query: {query}")
        logger.info(f"  → Location: {result['location']}")
        logger.info(f"  → Date: {result['date']}")
        logger.info(f"  → Valid: {result['success']}\n")

    logger.info("=== TESTING COMPLETE ===")


if __name__ == "__main__":
    main()
