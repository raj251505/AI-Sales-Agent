#  AI Sales Agent — Setup Guide

## Folder Structure
```
outreach_agent/
├── main.py              ← Run this
├── config.py            ← Settings
├── scraper.py           ← Google Maps scraper
├── scorer.py            ← Lead scoring engine
├── telegram_bot.py      ← Telegram notifications
├── outreach.py          ← AI email writer + Gmail sender
├── crm.py               ← Google Sheets CRM
├── scheduler.py         ← Follow up scheduler
├── requirements.txt     ← Python packages
├── .env                 ← Your API keys (create this)
├── credentials.json     ← Google service account (download this)
└── README.md
```

---

## Step 1 — Install packages
```bash
pip install -r requirements.txt --break-system-packages
playwright install chromium
```

---

## Step 2 — Get API Keys

### A. Gemini API Key (Free)
1. Go to https://aistudio.google.com
2. Click "Get API Key"
3. Create new key → Copy it

### B. Telegram Bot Token (Free)
1. Open Telegram → search @BotFather
2. Send /newbot
3. Give it a name and username
4. Copy the token it gives you
5. Send any message to your new bot
6. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
7. Copy the "id" number from "chat" object — that's your CHAT_ID

### C. Gmail App Password (Free)
1. Go to Google Account → Security
2. Make sure 2-Step Verification is ON
3. Search "App Passwords"
4. Create one → Select "Mail" → Copy the 16-character password

### D. Google Sheets API (Free)
1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable "Google Sheets API" and "Google Drive API"
4. Go to Credentials → Create Credentials → Service Account
5. Download the JSON key → rename it to credentials.json
6. Put credentials.json in this folder
7. Create a new Google Sheet
8. Share it with the service account email (from credentials.json → "client_email")
9. Copy the Sheet ID from the URL:
   https://docs.google.com/spreadsheets/d/[THIS_IS_THE_ID]/edit

---

## Step 3 — Create .env file
```bash
cp .env.example .env
```
Fill in all values in .env

---

## Step 4 — Run the Agent

### Option A: Use your already-scraped Excel file
```bash
python3 main.py
# Choose 1
# Enter path to your Excel file
```

### Option B: Scrape fresh + run agent
```bash
python3 main.py
# Choose 2
# Enter business type and city
```

---

## How it Works

1. Loads leads from Excel (your gym scraper output)
2. Scores each lead 1-10
3. Sends hot leads to your Telegram
4. You reply /approve_0 or /reject_0
5. On approve → AI writes personalized email → Gmail sends it
6. Google Sheets logs everything automatically
7. 48hrs later → auto follow up if no reply

---

## Telegram Commands
- `/approve_ID` → Approve a lead
- `/reject_ID` → Reject a lead  
- `/status` → See pipeline summary