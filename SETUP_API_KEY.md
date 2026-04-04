# Gemini API Key Setup Instructions

## Step 1: Get Your Free Gemini API Key

1. Go to: **https://makersuite.google.com/app/apikey**
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

## Step 2: Add API Key to Your Project

1. In your project root directory, create a file named `.env`

```bash
cd /Users/pavanbobba/Documents/master\'s_Project/Conversational-storm-analysis-prediction-using-NOAA-data
touch .env
```

2. Open `.env` and add your API key:

```
GEMINI_API_KEY=your_actual_api_key_here
```

**Example:**
```
GEMINI_API_KEY=AIzaSyABC123_your_real_key_here
```

## Step 3: Verify Setup

Run this command to verify your API key is configured:

```bash
source venv/bin/activate
python -c "from src.analytics.config import GEMINI_API_KEY; print('✅ API key configured!' if GEMINI_API_KEY and GEMINI_API_KEY != 'your_api_key_here' else '❌ API key not set')"
```

## Important Notes

- **Keep your API key secret!** Never commit `.env` to git
- The `.env` file is already in `.gitignore` for safety
- Gemini free tier: 60 requests/minute (plenty for this project)
- If you see warnings about API key, come back to this file

## Need Help?

If you have issues:
1. Make sure `.env` is in the project root (same level as src/)
2. Check that there are no extra spaces or quotes around your API key
3. Make sure you copied the full key (starts with "AIza...")

---

**Once your API key is set up, you can run the chatbot!**
