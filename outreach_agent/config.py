import os
from dotenv import load_dotenv

load_dotenv()

# AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Agent Identity
AGENT_NAME = os.getenv("AGENT_NAME", "Agent")
AGENT_SERVICE = os.getenv("AGENT_SERVICE", "Website Development")
AGENT_PORTFOLIO_URL = os.getenv("AGENT_PORTFOLIO_URL", "")
AGENT_PHONE = os.getenv("AGENT_PHONE", "")

# Scoring Thresholds
HOT_LEAD_SCORE = 7
MIN_LEAD_SCORE = 4

# Follow Up
FOLLOW_UP_HOURS = 48
MAX_FOLLOW_UPS = 2

# Scraper
MAX_RESULTS_PER_QUERY = 40
SCRAPER_DELAY_SECONDS = 2