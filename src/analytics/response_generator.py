"""
Groq-Powered Response Generator

Uses Groq API to generate natural language narratives from query results.
"""

from groq import Groq
from typing import Dict
from .config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE


class AnalyticsResponseGenerator:
    """Generate natural language responses using Groq"""

    def __init__(self, api_key: str = None):
        """
        Initialize response generator

        Args:
            api_key: Groq API key (uses config if not provided)
        """
        self.api_key = api_key or GROQ_API_KEY

        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError(
                "Groq API key not configured! "
                "Please set GROQ_API_KEY in your .env file."
            )

        # Configure Groq client
        self.client = Groq(api_key=self.api_key)

    def generate_response(self, parsed_query: Dict, results: Dict) -> str:
        """
        Generate natural language response from query results

        Args:
            parsed_query: Parsed query from GeminiQueryParser
            results: Query results from StormQueryEngine

        Returns:
            Markdown-formatted narrative response
        """
        # Check if we have results
        if results['summary']['total_events'] == 0:
            return self._generate_no_results_response(parsed_query)

        # Create prompt based on query type
        if parsed_query['output_mode'] == 'locations' and results.get('aggregated') is not None:
            return self._generate_location_response(parsed_query, results)
        else:
            return self._generate_event_list_response(parsed_query, results)

    def _generate_location_response(self, parsed_query: Dict, results: Dict) -> str:
        """Generate response for location-focused queries"""
        summary = results['summary']
        aggregated = results['aggregated']

        # Get top 10 locations
        top_locations = aggregated.head(10).to_dict('records')

        prompt = f"""You are analyzing NOAA storm data. Generate a clear, informative response.

User Query: "{parsed_query['raw_query']}"

Query Results:
- Total Events: {summary['total_events']:,}
- Date Range: {summary['date_range'][0]} to {summary['date_range'][1]}
- Total Deaths: {summary['total_deaths']:,}
- Total Injuries: {summary['total_injuries']:,}
- Total Damage: ${summary['total_damage']:,.0f}
- Number of Locations: {len(aggregated)}

Top 10 Locations by Event Count:
{self._format_location_table(top_locations)}

Generate a response that:
1. Starts with a clear summary answering the question
2. Lists the top 5-10 locations with their statistics
3. Includes total impact statistics
4. Uses markdown formatting (**bold** for numbers, bullet points for lists)
5. Is informative but concise (3-5 paragraphs)
6. Ends by mentioning the data table below

Do NOT include pleasantries, disclaimers, or references to being an AI."""

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a data analyst generating clear, informative storm analysis reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _generate_event_list_response(self, parsed_query: Dict, results: Dict) -> str:
        """Generate response for event list queries"""
        summary = results['summary']
        data = results['data']

        # Get sample of most significant events (by deaths or damage)
        if 'DEATHS_DIRECT' in data.columns:
            sample_events = data.nlargest(5, 'DEATHS_DIRECT')[[
                'EVENT_TYPE', 'STATE', 'CZ_NAME', 'BEGIN_DATE_TIME',
                'DEATHS_DIRECT', 'INJURIES_DIRECT', 'DAMAGE_PROPERTY'
            ]].head(5).to_dict('records')
        else:
            sample_events = data.head(5).to_dict('records')

        prompt = f"""You are analyzing NOAA storm data. Generate a clear, informative response.

User Query: "{parsed_query['raw_query']}"

Query Results:
- Total Events: {summary['total_events']:,}
- Date Range: {summary['date_range'][0]} to {summary['date_range'][1]}
- States Covered: {len(summary['states_covered'])} states
- Total Deaths: {summary['total_deaths']:,}
- Total Injuries: {summary['total_injuries']:,}
- Total Damage: ${summary['total_damage']:,.0f}

Most Significant Events:
{self._format_event_sample(sample_events)}

Generate a response that:
1. Starts with a clear summary answering the question
2. Mentions key statistics (total events, deaths, damage)
3. Highlights the most significant events (if applicable)
4. Uses markdown formatting (**bold** for emphasis, bullet points)
5. Is concise (2-4 paragraphs)
6. Ends by mentioning "See the data table below for complete details"

Do NOT include pleasantries, disclaimers, or references to being an AI."""

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a data analyst generating clear, informative storm analysis reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _generate_no_results_response(self, parsed_query: Dict) -> str:
        """Generate response when no results found"""
        prompt = f"""The user asked: "{parsed_query['raw_query']}"

No storm events were found matching these criteria.

Generate a helpful response that:
1. Clearly states no events were found
2. Suggests why (e.g., filters too specific, rare event type, location/time combination)
3. Offers suggestions to broaden the search
4. Is brief and helpful

Do NOT include pleasantries or apologies."""

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _format_location_table(self, locations: list) -> str:
        """Format location data for prompt"""
        lines = []
        for i, loc in enumerate(locations, 1):
            lines.append(
                f"{i}. {loc['location']}: {loc['event_count']} events, "
                f"{loc['total_deaths']} deaths, "
                f"${loc['total_damage']:,.0f} damage"
            )
        return '\n'.join(lines)

    def _format_event_sample(self, events: list) -> str:
        """Format event data for prompt"""
        lines = []
        for i, event in enumerate(events, 1):
            date = str(event.get('BEGIN_DATE_TIME', 'N/A'))[:10]
            lines.append(
                f"{i}. {event.get('EVENT_TYPE', 'Unknown')} - "
                f"{event.get('CZ_NAME', 'N/A')}, {event.get('STATE', 'N/A')} "
                f"({date})"
            )
        return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    print("Response generator created successfully!")
    print("This module requires Gemini API key to be configured.")
    print("Get your key from: https://makersuite.google.com/app/apikey")
