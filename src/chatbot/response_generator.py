"""
Response Generator Module
Formats storm predictions into natural language responses
"""
from typing import Dict


class ResponseGenerator:
    """
    Generates natural language responses for storm predictions
    """

    def __init__(self):
        """Initialize response generator"""
        pass

    def generate_response(self, result: Dict) -> str:
        """
        Generate natural language response from prediction result

        Args:
            result: Prediction result dictionary from orchestrator

        Returns:
            Formatted natural language response
        """
        if not result['success']:
            return result.get('error', "I couldn't process your query. Please try again.")

        # Route based on query type
        query_type = result.get('query_type', 'specific_date')

        if query_type == 'year_only':
            return self.generate_yearly_response(result)
        else:
            return self.generate_specific_date_response(result)

    def generate_specific_date_response(self, result: Dict) -> str:
        """
        Generate response for specific date queries

        Args:
            result: Prediction result dictionary

        Returns:
            Formatted response
        """
        # Extract data
        location = result['location_name']
        date = result['date']
        probability = result['probability']
        risk_level = result['risk_level']
        season = result['season']

        # Build main response
        response = (
            f"Based on historical patterns, there is a **{probability:.1%} chance** "
            f"of storm activity in {location} on {date}. "
            f"This represents a **{risk_level.lower()} risk** period."
        )

        # Add seasonal context
        seasonal_context = self._get_seasonal_context(
            location, season, risk_level, probability
        )

        if seasonal_context:
            response += f"\n\n{seasonal_context}"

        # Add disclaimer
        disclaimer = (
            "\n\n_Note: This prediction is based on historical weather patterns from 2015-2025 "
            "and should not be used as a substitute for professional weather forecasts._"
        )

        response += disclaimer

        return response

    def generate_yearly_response(self, result: Dict) -> str:
        """
        Generate response for year-only queries

        Args:
            result: Prediction result with yearly_data

        Returns:
            Formatted response with monthly breakdown
        """
        location = result['location_name']
        year = result['year']
        yearly_data = result['yearly_data']

        # Build response header
        response = f"## Storm Risk Forecast for {location} in {year}\n\n"

        # Peak months
        if yearly_data['peak_months']:
            response += "**Peak Risk Months (High):**\n"
            for month_data in yearly_data['monthly_predictions']:
                if month_data['month_name'] in yearly_data['peak_months']:
                    response += f"- **{month_data['month_name']}**: {month_data['probability']:.1%} probability\n"
            response += "\n"

        # Low months
        if yearly_data['low_months']:
            response += "**Low Risk Months:**\n"
            for month_data in yearly_data['monthly_predictions']:
                if month_data['month_name'] in yearly_data['low_months']:
                    response += f"- {month_data['month_name']}: {month_data['probability']:.1%} probability\n"
            response += "\n"

        # Overall average
        avg = yearly_data['average_probability']
        response += f"**Annual Average Risk**: {avg:.1%}\n\n"

        # Seasonal advice based on peak months
        if yearly_data['peak_months']:
            peak_list = ", ".join(yearly_data['peak_months'])
            response += f"**Recommendation**: Highest storm activity expected in {peak_list}. "
            response += "Monitor weather forecasts closely during these months.\n"

        # Disclaimer
        response += (
            "\n_Note: This prediction is based on historical weather patterns from 2015-2025 "
            "and should not be used as a substitute for professional weather forecasts._"
        )

        return response

    def _get_seasonal_context(
        self,
        location: str,
        season: str,
        risk_level: str,
        probability: float
    ) -> str:
        """
        Generate contextual information based on season and location

        Args:
            location: Location name
            season: Season name
            risk_level: Risk level (Low/Medium/High)
            probability: Probability score

        Returns:
            Seasonal context string
        """
        contexts = []

        # Season-specific context
        if season == "Spring":
            if risk_level == "High":
                contexts.append("Spring is typically active for severe weather, including tornadoes and thunderstorms.")
            else:
                contexts.append("Spring weather can be variable in this region.")

        elif season == "Summer":
            if risk_level == "High":
                contexts.append("Summer is peak storm season in many areas, with frequent thunderstorms and potential hurricanes.")
            else:
                contexts.append("Summer typically brings warmer, more humid conditions.")

        elif season == "Fall":
            if risk_level == "High":
                contexts.append("Fall can bring late-season hurricanes and transitional severe weather.")
            elif risk_level == "Medium":
                contexts.append("Fall represents a transition period with decreasing storm activity.")

        elif season == "Winter":
            if risk_level == "High":
                contexts.append("Winter storms in this region can include snow, ice, and severe thunderstorms.")
            else:
                contexts.append("Winter is typically a calmer period for severe weather in most regions.")

        # Risk-level specific advice
        if risk_level == "High":
            contexts.append("Stay informed about weather conditions if planning outdoor activities.")
        elif risk_level == "Medium":
            contexts.append("Monitor weather forecasts as conditions approach.")

        return " ".join(contexts) if contexts else ""

    def generate_short_response(self, result: Dict) -> str:
        """
        Generate brief response (for chat interfaces)

        Args:
            result: Prediction result dictionary

        Returns:
            Short formatted response
        """
        if not result['success']:
            return result.get('error', "Unable to process query.")

        location = result['location_name']
        date = result['date']
        probability = result['probability']
        risk_level = result['risk_level']

        return (
            f"{probability:.1%} chance ({risk_level.lower()} risk) "
            f"for {location} on {date}"
        )


def main():
    """
    Test response generator
    """
    generator = ResponseGenerator()

    # Example prediction result
    test_result = {
        'success': True,
        'query': 'Will there be a storm in Atlanta on August 18, 2028?',
        'location_name': 'Atlanta',
        'coordinates': (33.75, -84.39),
        'date': '2028-08-18',
        'probability': 0.775,
        'risk_level': 'High',
        'season': 'Summer'
    }

    print("=== TESTING RESPONSE GENERATOR ===\n")

    print("Full Response:")
    print("-" * 80)
    print(generator.generate_response(test_result))
    print()

    print("\nShort Response:")
    print("-" * 80)
    print(generator.generate_short_response(test_result))
    print()

    # Test error response
    error_result = {
        'success': False,
        'error': 'Location not found'
    }

    print("\nError Response:")
    print("-" * 80)
    print(generator.generate_response(error_result))


if __name__ == "__main__":
    main()
