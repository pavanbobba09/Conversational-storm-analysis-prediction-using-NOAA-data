# 🚀 Quick Start Guide - Storm Analytics Chatbot

## ✅ What's Been Implemented

Your Gemini-powered storm analytics chatbot is ready! Here's what we built:

### Core Components ✅
1. **Query Parser** - Uses Gemini AI to understand natural language
2. **Query Engine** - Filters 436k NOAA storm records with pandas
3. **Response Generator** - Uses Gemini AI to create narratives
4. **Table Formatter** - Formats data for web display
5. **Excel Exporter** - Generates research-ready Excel files
6. **Orchestrator** - Coordinates all components
7. **Gradio Web UI** - Beautiful chat interface

### Technology Stack
- **AI:** Google Gemini 1.5 Flash (free tier!)
- **Data:** NOAA Storm Events (436,305 records, 2015-2025)
- **Processing:** Pandas (in-memory, fast)
- **UI:** Gradio web framework

---

## 📋 Next Steps

### Step 1: Get Your Gemini API Key (5 minutes)

1. Go to: **https://makersuite.google.com/app/apikey**
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key (starts with "AIza...")

### Step 2: Configure API Key

```bash
# Navigate to project
cd /Users/pavanbobba/Documents/master\'s_Project/Conversational-storm-analysis-prediction-using-NOAA-data

# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**Replace `your_api_key_here` with your actual API key!**

### Step 3: Launch the Chatbot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the chatbot
python src/interfaces/gradio_analytics_app.py
```

### Step 4: Open in Browser

Open: **http://localhost:7860**

---

## 🎯 Try These Queries

Once the chatbot is running, try these example queries:

### Simple Queries
- "Show me all locations where tornadoes occurred in the last 5 years"
- "Show me all places where hurricane deaths occurred in 2020"
- "Show me events where flooding occurred in Texas in 2020"

### Advanced Queries
- "Give me a list of all wind-related events in the last 10 years"
- "Show me all wind-related events with deaths and property damage in 2020"
- "What were the deadliest tornado events in Oklahoma?"

---

## 📊 What You'll Get

For each query, the chatbot provides:

1. **📝 Narrative Answer** - AI-generated summary with key insights
2. **📋 Data Table** - Top 100 events formatted for quick viewing
3. **📥 Excel File** - Complete data with ALL 54 NOAA columns (unmodified, research-ready)

### Excel File Structure
- **Sheet 1:** Summary (narrative + statistics)
- **Sheet 2:** Data (EXACT NOAA records - all rows, all columns)
- **Sheet 3:** Metadata (column descriptions + data dictionary)

---

## 🔧 Troubleshooting

### "API key not configured" Error

Make sure you:
1. Created `.env` file in project root
2. Added `GEMINI_API_KEY=your_key` (no spaces, no quotes)
3. Used your actual API key (not "your_api_key_here")

**Verify:**
```bash
python -c "from src.analytics.config import GEMINI_API_KEY; print('✅ Configured' if GEMINI_API_KEY else '❌ Not set')"
```

### Port Already in Use

If port 7860 is busy:
```bash
# Kill existing process
lsof -ti:7860 | xargs kill -9

# Or use different port
python src/interfaces/gradio_analytics_app.py --server-port 7861
```

### Import Errors

Make sure virtual environment is activated:
```bash
source venv/bin/activate
pip list | grep -E "google-generativeai|gradio|pandas"
```

---

## 📚 Documentation

- **SETUP_API_KEY.md** - Detailed API key setup
- **CLAUDE.md** - Project details for future sessions
- **README.md** - Full project documentation

---

## 🎓 For Your Professor

This chatbot demonstrates:
- ✅ Natural language query understanding (Gemini AI)
- ✅ Historical pattern extraction from NOAA data
- ✅ Meaningful narrative responses (Gemini AI)
- ✅ Research-ready data exports (Excel)
- ✅ 436k records (10.5 years of storm data)

**No predictions** - Pure historical analytics as requested!

---

## ⚡ Quick Commands

```bash
# Start chatbot
source venv/bin/activate && python src/interfaces/gradio_analytics_app.py

# Check API key
python -c "from src.analytics.config import GEMINI_API_KEY; print(GEMINI_API_KEY[:10] + '...' if GEMINI_API_KEY else 'NOT SET')"

# Test query (after API key is set)
python src/chatbot/analytics_orchestrator.py
```

---

## 💡 Tips

1. **API Key is Free!** - Gemini free tier: 60 requests/minute
2. **Data Stays Local** - Only queries sent to Gemini, data never leaves your computer
3. **Excel Always Generated** - Every query creates a downloadable Excel file
4. **Natural Language** - Ask questions naturally, Gemini understands context

---

**Ready? Add your API key and launch the chatbot!** 🚀
