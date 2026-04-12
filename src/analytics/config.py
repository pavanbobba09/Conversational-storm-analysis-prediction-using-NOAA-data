"""
Configuration management for Storm Analytics Chatbot
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Groq API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

if not GROQ_API_KEY or GROQ_API_KEY == 'your_api_key_here':
    print("⚠️  Warning: GROQ_API_KEY not set!")
    print("   Please create a .env file and add your Groq API key:")
    print("   GROQ_API_KEY=your_actual_key_here")
    print()
    print("   Get your key from: https://console.groq.com/")
    print()

# Groq Model Configuration
GROQ_MODEL = 'llama-3.3-70b-versatile'  # Fast and capable model
GROQ_TEMPERATURE = 0.1  # Low temperature for consistent, factual responses

# Data Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = PROJECT_ROOT / 'data' / 'processed' / 'storms_raw.parquet'

# Cache Paths
CACHE_DIR = PROJECT_ROOT / 'data' / 'processed'
PICKLE_CACHE_PATH = CACHE_DIR / 'storms_raw_cached.pkl'
PARQUET_CACHE_PATH = CACHE_DIR / 'storms_raw.parquet'

# Cache Settings
CACHE_ENABLED = True  # Enable pickle caching for 3x faster startup
PICKLE_PROTOCOL = 5  # Python 3.8+ optimized protocol

# Query Configuration
MAX_RESULTS_DISPLAY = 100  # Max rows to show in Gradio UI
DEFAULT_YEAR_RANGE = 5  # Default years for "last X years" queries
