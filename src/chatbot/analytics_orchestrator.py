"""
Analytics Orchestrator

Coordinates all components for end-to-end query processing:
1. Parse query with Groq
2. Execute query with pandas
3. Generate narrative with Groq
4. Format table for display
5. Generate Excel export
"""

import pandas as pd
from typing import Dict
import sys
sys.path.append('..')

from src.analytics.query_parser_gemini import GroqQueryParser
from src.analytics.query_engine import StormQueryEngine
from src.analytics.response_generator import AnalyticsResponseGenerator
from src.analytics.table_formatter import TableFormatter
from src.analytics.excel_exporter import ExcelExporter
from src.analytics.config import DATA_PATH


class AnalyticsOrchestrator:
    """Coordinate all components for analytics queries"""

    def __init__(self, api_key: str = None, data_path: str = None):
        """
        Initialize orchestrator with all components

        Args:
            api_key: Groq API key (uses config if not provided)
            data_path: Path to NOAA data file
        """
        print("🔄 Initializing Storm Analytics Chatbot...")

        # Initialize components
        try:
            self.parser = GroqQueryParser(api_key=api_key)
            print("✅ Query parser initialized (Groq)")
        except ValueError as e:
            print(f"❌ {e}")
            raise

        data_file = data_path or str(DATA_PATH)
        self.engine = StormQueryEngine(data_file)
        print("✅ Query engine initialized")

        try:
            self.response_generator = AnalyticsResponseGenerator(api_key=api_key)
            print("✅ Response generator initialized (Groq)")
        except ValueError as e:
            print(f"❌ {e}")
            raise

        self.table_formatter = TableFormatter()
        print("✅ Table formatter initialized")

        self.excel_exporter = ExcelExporter()
        print("✅ Excel exporter initialized")

        print("🎉 Storm Analytics Chatbot ready!\n")

    def process_query(self, query: str) -> Dict:
        """
        Process query end-to-end

        Args:
            query: Natural language query from user

        Returns:
            Dictionary with all results:
            {
                'success': bool,
                'narrative': str (Markdown),
                'data_table': pd.DataFrame (formatted for display),
                'excel_file': str (filepath),
                'metadata': dict (query info, counts, etc.)
            }
        """
        try:
            print(f"\n📝 Processing query: \"{query}\"")

            # Step 1: Parse query with Gemini
            print("  🔍 Parsing query with Gemini...")
            parsed = self.parser.parse(query)
            print(f"  ✅ Parsed: {parsed['query_type']}")

            # Step 2: Execute query
            print("  🔎 Filtering NOAA data...")
            results = self.engine.execute_query(parsed)
            print(f"  ✅ Found {results['summary']['total_events']:,} events")

            # Step 3: Generate narrative with Gemini
            print("  📄 Generating narrative with Gemini...")
            narrative = self.response_generator.generate_response(parsed, results)
            print("  ✅ Narrative generated")

            # Step 4: Format table for display
            print("  📋 Formatting data table...")
            display_table = self.table_formatter.format_for_display(
                results['data'],
                parsed,
                results.get('aggregated')
            )
            print(f"  ✅ Table formatted ({len(display_table)} rows for display)")

            # Step 5: Generate Excel export
            print("  📊 Generating Excel export...")
            excel_file = self.excel_exporter.generate_excel(
                parsed,
                results,
                narrative
            )
            print(f"  ✅ Excel file generated: {excel_file}")

            # Prepare metadata
            metadata = {
                'query_type': parsed['query_type'],
                'result_count': results['summary']['total_events'],
                'display_count': len(display_table),
                'date_range': f"{results['summary']['date_range'][0]} to {results['summary']['date_range'][1]}" if results['summary']['date_range'][0] else "N/A",
                'states': ', '.join(results['summary']['states_covered'][:5]) + ('...' if len(results['summary']['states_covered']) > 5 else ''),
                'excel_filename': excel_file.split('/')[-1]
            }

            print("✅ Query processed successfully!\n")

            return {
                'success': True,
                'narrative': narrative,
                'data_table': display_table,
                'excel_file': excel_file,
                'metadata': metadata,
                'raw_data': results['data']  # For advanced use
            }

        except Exception as e:
            print(f"❌ Error processing query: {e}\n")
            return {
                'success': False,
                'narrative': f"**Error:** {str(e)}\n\nPlease try rephrasing your question or check your API key configuration.",
                'data_table': pd.DataFrame(),
                'excel_file': None,
                'metadata': {
                    'query_type': 'error',
                    'result_count': 0,
                    'display_count': 0,
                    'date_range': 'N/A',
                    'states': 'N/A'
                },
                'error': str(e)
            }

    def get_example_queries(self) -> list:
        """Get list of example queries"""
        return [
            "Show me all locations where tornadoes occurred in the last 5 years",
            "Show me all places where hurricane deaths occurred in 2020",
            "Show me events where flooding occurred in Texas in 2020",
            "Give me a list of all wind-related events in the last 10 years",
            "Show me all wind-related events with deaths and property damage in 2020",
            "What were the deadliest tornado events in Oklahoma?",
            "List all hail events in Kansas in 2020",
            "Show me flooding events with over $1M damage in 2020"
        ]


# Example usage
if __name__ == "__main__":
    try:
        # Initialize orchestrator
        orchestrator = AnalyticsOrchestrator()

        # Test query
        query = "Show me all locations where tornadoes occurred in the last 5 years"
        result = orchestrator.process_query(query)

        if result['success']:
            print("\n=== NARRATIVE ===")
            print(result['narrative'])

            print("\n=== DATA TABLE ===")
            print(result['data_table'].head())

            print("\n=== METADATA ===")
            for key, value in result['metadata'].items():
                print(f"{key}: {value}")

            print(f"\n=== EXCEL FILE ===")
            print(f"Download: {result['excel_file']}")

    except ValueError as e:
        print(f"\n{e}")
        print("\nPlease follow the setup instructions in SETUP_API_KEY.md")
