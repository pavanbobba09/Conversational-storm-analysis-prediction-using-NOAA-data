"""
Gradio Web Interface for Storm Forecasting Chatbot
Interactive web UI for natural language storm predictions
"""
import sys
from pathlib import Path
from loguru import logger
import gradio as gr

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from chatbot.orchestrator import ChatbotOrchestrator
from chatbot.response_generator import ResponseGenerator


class GradioStormChatbot:
    """
    Gradio web interface for storm forecasting chatbot
    """

    def __init__(self):
        """Initialize Gradio interface"""
        logger.info("Initializing Gradio Storm Chatbot...")

        # Paths
        model_path = str(Path(__file__).parent.parent.parent / "models" / "storm_predictor_v1.pkl")
        geocoding_file = str(Path(__file__).parent.parent.parent / "data" / "geocoding" / "us_cities.json")
        historical_data_path = str(Path(__file__).parent.parent.parent / "data" / "processed" / "storms_features.parquet")

        # Initialize components
        self.orchestrator = ChatbotOrchestrator(
            model_path=model_path,
            geocoding_file=geocoding_file,
            historical_data_path=historical_data_path
        )

        self.response_generator = ResponseGenerator()

        logger.info("Gradio chatbot initialized!")

    def predict(self, query: str) -> tuple:
        """
        Process user query and return formatted response

        Args:
            query: User's natural language query

        Returns:
            Tuple of (response_text, probability, risk_level, location, date)
        """
        if not query or not query.strip():
            return ("Please enter a question about storm forecasts.", "", "", "", "")

        try:
            # Process query
            result = self.orchestrator.process_query(query)

            if result['success']:
                # Generate response
                response = self.response_generator.generate_response(result)

                # Extract metadata based on query type
                query_type = result.get('query_type', 'specific_date')
                location = f"{result['location_name']} ({result['coordinates'][0]:.2f}, {result['coordinates'][1]:.2f})"

                if query_type == 'year_only':
                    # Year-only query metadata
                    yearly_data = result['yearly_data']
                    probability = f"{yearly_data['average_probability']:.1%} (annual avg)"

                    # Determine overall risk based on average
                    avg_prob = yearly_data['average_probability']
                    if avg_prob < 0.3:
                        risk_level = "Low (annual)"
                    elif avg_prob < 0.6:
                        risk_level = "Medium (annual)"
                    else:
                        risk_level = "High (annual)"

                    date = f"Year {result['year']} (all months)"

                else:
                    # Specific date query metadata
                    probability = f"{result['probability']:.1%}"
                    risk_level = result['risk_level']
                    date = f"{result['date']} ({result['season']})"

                return (response, probability, risk_level, location, date)

            else:
                # Error response
                error_msg = result.get('error', 'Unable to process query')
                return (error_msg, "", "", "", "")

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return (f"Error: {str(e)}", "", "", "", "")

    def create_interface(self):
        """
        Create Gradio interface

        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(title="Storm Forecasting Chatbot", theme=gr.themes.Soft()) as interface:
            gr.Markdown(
                """
                # 🌩️ Storm Forecasting Chatbot

                Ask natural language questions about storm likelihood for any US location and future date!

                **Powered by:**
                - 🤖 BERT NLP for query understanding
                - 📊 XGBoost ML model trained on 1.3M+ historical storm events (2015-2025)
                - 📍 Geographic coverage of 3,600+ US locations

                **Example queries:**
                - "Will there be a storm in Atlanta on August 18, 2028?"
                - "Hurricane risk in New Orleans on September 15, 2028?"
                - "Tornado forecast for Oklahoma City on May 15, 2028"
                """
            )

            with gr.Row():
                with gr.Column(scale=2):
                    # Input
                    query_input = gr.Textbox(
                        label="Your Question",
                        placeholder="Will there be a storm in Miami on July 4, 2028?",
                        lines=2
                    )

                    # Submit button
                    submit_btn = gr.Button("Get Forecast", variant="primary", size="lg")

                    # Example queries
                    gr.Examples(
                        examples=[
                            ["Will there be a storm in Atlanta on August 18, 2028?"],
                            ["Hurricane risk in New Orleans on September 15, 2028?"],
                            ["Tornado forecast for Oklahoma City on May 15, 2028"],
                            ["Storm probability in Miami on July 4, 2028"],
                            ["Will Seattle have storms on December 25, 2028?"],
                            ["Thunderstorm chance in New York on March 15, 2028"],
                        ],
                        inputs=query_input,
                        label="Try these examples:"
                    )

                with gr.Column(scale=1):
                    # Metadata outputs
                    gr.Markdown("### 📊 Prediction Details")

                    probability_output = gr.Textbox(
                        label="Storm Probability",
                        interactive=False
                    )

                    risk_level_output = gr.Textbox(
                        label="Risk Level",
                        interactive=False
                    )

                    location_output = gr.Textbox(
                        label="Location",
                        interactive=False
                    )

                    date_output = gr.Textbox(
                        label="Date & Season",
                        interactive=False
                    )

            # Main response output
            response_output = gr.Markdown(
                label="Forecast Response",
                value="*Enter a question above to get started*"
            )

            # Connect interface
            submit_btn.click(
                fn=self.predict,
                inputs=[query_input],
                outputs=[response_output, probability_output, risk_level_output, location_output, date_output]
            )

            # Also submit on Enter key
            query_input.submit(
                fn=self.predict,
                inputs=[query_input],
                outputs=[response_output, probability_output, risk_level_output, location_output, date_output]
            )

            gr.Markdown(
                """
                ---

                ### ℹ️ About This Model

                This chatbot uses machine learning to predict storm probability based on:
                - **Historical patterns** from 10+ years of NOAA storm data (2015-2025)
                - **Temporal features**: Month, season, day of year
                - **Spatial features**: Geographic location (latitude/longitude)
                - **Historical statistics**: Past storm frequency for the location

                **Model Performance:**
                - ROC-AUC: 0.8736 (87% accuracy in distinguishing storm vs. no-storm days)
                - F1-Score: 0.72
                - Trained on 1,308,915 samples

                **Important:** This is NOT a real-time weather forecast. It shows historical risk patterns
                and should not replace professional meteorological forecasts.

                ---

                Built with ❤️ using BERT NLP, XGBoost ML, and Gradio | Data: NOAA Storm Events Database
                """
            )

        return interface

    def launch(self, share=False):
        """
        Launch Gradio interface

        Args:
            share: Whether to create public shareable link
        """
        interface = self.create_interface()
        interface.launch(share=share, server_name="0.0.0.0", server_port=7860)


def main():
    """
    Launch Gradio Storm Chatbot
    """
    logger.info("=== LAUNCHING STORM FORECASTING CHATBOT ===\n")

    app = GradioStormChatbot()

    logger.info("Starting Gradio interface...")
    logger.info("Access the app at: http://localhost:7860")
    logger.info("Press Ctrl+C to stop\n")

    app.launch(share=False)


if __name__ == "__main__":
    main()
