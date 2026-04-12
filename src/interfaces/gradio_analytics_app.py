"""
Gradio Web UI for Storm Analytics Chatbot

Powered by:
- Groq API for natural language understanding and response generation
- Pandas for data filtering
- NOAA Storm Events Database (1.1M records, 1996-2025)
"""

import gradio as gr
import pandas as pd
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.chatbot.analytics_orchestrator import AnalyticsOrchestrator


def create_interface():
    """Create Gradio interface for storm analytics chatbot"""

    # Initialize orchestrator (will check for API key)
    try:
        orchestrator = AnalyticsOrchestrator()
        api_key_status = "✅ Groq API configured"
    except ValueError as e:
        orchestrator = None
        api_key_status = f"❌ {str(e)}"
        print("\n" + "="*60)
        print("⚠️  GROQ API KEY NOT CONFIGURED")
        print("="*60)
        print("\nPlease follow these steps:")
        print("1. Get your free API key: https://console.groq.com/")
        print("2. Create a .env file in the project root")
        print("3. Add: GROQ_API_KEY=your_key_here")
        print("\nSee SETUP_API_KEY.md for detailed instructions.")
        print("="*60 + "\n")

    def process_query(query: str):
        """Process user query"""
        if not orchestrator:
            return (
                "**⚠️ API Key Not Configured**\n\n" +
                "Please set up your Groq API key first.\n\n" +
                "See `SETUP_API_KEY.md` for instructions.",
                pd.DataFrame(),
                None,
                "error",
                "0 events",
                "N/A"
            )

        if not query.strip():
            return (
                "*Enter a question above to start analyzing storm data*",
                pd.DataFrame(),
                None,
                "",
                "",
                ""
            )

        # Process query
        result = orchestrator.process_query(query)

        return (
            result['narrative'],
            result['data_table'],
            result['excel_file'],
            result['metadata'].get('query_type', 'N/A'),
            f"{result['metadata'].get('result_count', 0):,} events",
            result['metadata'].get('date_range', 'N/A')
        )

    # Create Gradio interface
    with gr.Blocks(theme=gr.themes.Soft(), title="Storm Analytics Chatbot") as app:

        # Header
        gr.Markdown("# 🌪️ NOAA Storm Analytics Chatbot")
        gr.Markdown("*Powered by Groq AI + NOAA Storm Events Database (1996-2025)*")

        # API Status
        gr.Markdown(f"**API Status:** {api_key_status}")

        with gr.Row():
            with gr.Column(scale=3):
                # Query input
                query_input = gr.Textbox(
                    label="Ask a Question",
                    placeholder="Show me all places where hurricane deaths occurred in 2020",
                    lines=3
                )

                with gr.Row():
                    submit_btn = gr.Button("🔍 Analyze", variant="primary", size="lg")
                    clear_btn = gr.Button("🗑️ Clear", size="lg")

                # Example queries
                gr.Examples(
                    examples=[
                        ["Show me all locations where tornadoes occurred in the last 5 years"],
                        ["Show me all places where hurricane deaths occurred in 2020"],
                        ["Show me events where flooding occurred in Texas in 2020"],
                        ["Give me a list of all wind-related events in the last 10 years"],
                        ["Show me all wind-related events with deaths and property damage in 2020"],
                        ["What were the deadliest tornado events in Oklahoma?"],
                        ["List all hail events in Kansas in 2020"],
                    ],
                    inputs=query_input,
                    label="💡 Example Queries (Click to try)"
                )

            with gr.Column(scale=1):
                # Metadata panel
                gr.Markdown("### 📊 Query Info")
                query_type_display = gr.Textbox(label="Query Type", interactive=False)
                result_count_display = gr.Textbox(label="Results Found", interactive=False)
                date_range_display = gr.Textbox(label="Date Range", interactive=False)

        # Divider
        gr.Markdown("---")

        # Output: Narrative
        gr.Markdown("### 📝 Analysis")
        narrative_output = gr.Markdown(
            value="*Enter a question above to start analyzing storm data*"
        )

        # Output: Data Table
        gr.Markdown("### 📋 Data Table")
        gr.Markdown("*Showing first 100 rows. Download Excel for complete data.*")
        table_output = gr.DataFrame(
            label="Storm Events",
            wrap=True,
            interactive=False
        )

        # Output: Excel Download
        excel_output = gr.File(
            label="📥 Download Complete Data (Excel)",
            visible=True
        )

        # Help section
        with gr.Accordion("ℹ️ How to Use", open=False):
            gr.Markdown("""
            ## Supported Query Patterns

            **Location-Based Queries:**
            - "Show me all **locations** where [event type] occurred in [time period]"
            - "Show me all **places** where [event type] [metric] occurred in [year]"

            **Event List Queries:**
            - "Show me **events** where [event type] occurred in [location] in [time]"
            - "List all [event type] with [metric filters]"
            - "Give me a list of [event type] in [time period]"

            ## Available Filters

            **Event Types:**
            - Tornadoes, hurricanes, floods, hail, wind, thunderstorms, lightning

            **Locations:**
            - US state names (e.g., Texas, Florida, Oklahoma)

            **Time Periods:**
            - "last 5 years", "last 10 years"
            - "in 2020", "in 2021"
            - "between 2015 and 2020"

            **Metrics:**
            - deaths, fatalities, casualties
            - injuries
            - damage, property damage, crop damage

            ## Data Source

            - **Database:** NOAA Storm Events (1996-2025)
            - **Records:** 1,117,547 validated storm events
            - **Coverage:** All 50 US states + territories
            - **Powered by:** Groq AI for natural language understanding

            ## Excel Export

            Every query generates an Excel file with:
            - **Sheet 1:** Summary (narrative + statistics)
            - **Sheet 2:** Data (exact NOAA records - ALL rows, ALL 54 columns)
            - **Sheet 3:** Metadata (column descriptions)

            **Note:** Excel contains complete, unmodified NOAA data suitable for research.
            """)

        # About section
        with gr.Accordion("ℹ️ About", open=False):
            gr.Markdown("""
            ## Storm Analytics Chatbot

            This chatbot helps you explore and analyze historical storm data from NOAA's Storm Events Database.

            **Technology Stack:**
            - **AI:** Groq LLaMA 3.3 70B (query understanding + narrative generation)
            - **Data:** NOAA Storm Events Database (1996-2025, 1.1M events)
            - **Processing:** Pandas (fast filtering and aggregation)
            - **Interface:** Gradio Web UI

            **Features:**
            - Natural language query understanding
            - AI-generated narrative responses
            - Interactive data tables
            - Excel export with exact NOAA data
            - Fast inference with Groq

            **Created for:** Master's project on conversational storm data analysis

            ---

            **Data Disclaimer:**
            This tool provides historical storm data for research and educational purposes.
            It is not a weather forecasting tool and should not be used for real-time weather decisions.
            """)

        # Footer
        gr.Markdown("""
        ---
        **Data Source:** NOAA Storm Events Database (1996-2025) | **Records:** 1,117,547 events | **Coverage:** All 50 US states + territories

        *Powered by Groq AI*
        """)

        # Connect components
        submit_btn.click(
            fn=process_query,
            inputs=[query_input],
            outputs=[
                narrative_output,
                table_output,
                excel_output,
                query_type_display,
                result_count_display,
                date_range_display
            ]
        )

        clear_btn.click(
            fn=lambda: ("", pd.DataFrame(), None, "", "", ""),
            inputs=[],
            outputs=[
                query_input,
                table_output,
                excel_output,
                query_type_display,
                result_count_display,
                date_range_display
            ]
        )

    return app


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌪️  NOAA Storm Analytics Chatbot")
    print("="*60)
    print("\nStarting Gradio web interface...")

    app = create_interface()

    print("\n✅ Gradio server starting...")
    print("📱 Open in browser: http://localhost:7860")
    print("\n💡 Tip: Use Ctrl+C to stop the server\n")

    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
