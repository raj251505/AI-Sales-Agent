import time
import re
from google import genai
from telegram import Bot
from config import (
    GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    AGENT_NAME, AGENT_SERVICE, AGENT_PORTFOLIO_URL, AGENT_PHONE
)


def clean_phone(phone: str) -> str:
    if not phone:
        return ""

    digits_only = re.sub(r'[^\d+]', '', phone)

    if digits_only.startswith("+91"):
        digits_only = digits_only[3:]
    elif digits_only.startswith("91") and len(digits_only) == 12:
        digits_only = digits_only[2:]

    if digits_only.startswith("0"):
        digits_only = digits_only[1:]

    if len(digits_only) == 10:
        return f"+91{digits_only}"

    return ""


def write_outreach_message(lead: dict, is_followup: bool = False, followup_num: int = 1) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)

    business_name = lead.get("name", "your business")
    address       = lead.get("address", "")
    rating        = lead.get("rating", "")
    reviews       = lead.get("reviews", "")

    if not is_followup:
        prompt = f"""
You are {AGENT_NAME}, a professional web developer reaching out to a local business owner on WhatsApp.

Write a SHORT, friendly, personalized WhatsApp message to get a quick call or reply.

Business Details:
- Name: {business_name}
- Address: {address}
- Google Rating: {rating} stars with {reviews} reviews
- They currently have NO website

Your service: {AGENT_SERVICE}
Your portfolio: {AGENT_PORTFOLIO_URL}
Your phone: {AGENT_PHONE}

Rules:
- Under 80 words total
- WhatsApp style — casual, warm, human
- Mention ONE specific thing about their business (rating or location)
- Focus on what they GAIN — more customers, look professional
- End with a simple question like "Would you be open to a quick 5 min call?"
- Max 2 emojis
- Do NOT sound like a bulk message or template
- Do NOT use words like "leverage", "synergy", "cutting-edge"
- Sign off with your name and phone number

Return ONLY the message text, nothing else.
        """
    else:
        prompt = f"""
You are {AGENT_NAME}, sending a follow up WhatsApp message (#{followup_num}) to {business_name}.

They have no website. You offer: {AGENT_SERVICE}
Your phone: {AGENT_PHONE}

Rules:
- Under 50 words
- Reference your previous message naturally
- Try a different angle (mention a competitor having a website, or a specific benefit)
- One clear CTA — reply or call
- Friendly, not pushy
- Max 1 emoji

Return ONLY the message text, nothing else.
        """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text.strip()


def send_whatsapp(phone: str, message: str) -> bool:
    try:
        import os
        import pywhatkit  # lazy import — requires X display only when actually sending
        os.environ.setdefault('DISPLAY', ':0')

        cleaned = clean_phone(phone)
        if not cleaned:
            print(f"   Invalid phone number: {phone}")
            return False

        print(f"   Sending WhatsApp to {cleaned}...")

        pywhatkit.sendwhatmsg_instantly(
            phone_no=cleaned,
            message=message,
            wait_time=12,
            tab_close=True,
            close_time=3
        )

        time.sleep(5)
        print(f"   WhatsApp sent to {cleaned}")
        return True

    except Exception as e:
        print(f"   WhatsApp send failed: {e}")
        return False


async def notify_outreach_sent(lead: dict, message: str) -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    phone = clean_phone(lead.get("phone", ""))

    confirmation = f"""
*Outreach Sent!*
━━━━━━━━━━━━━━━━━━━━
*{lead['name']}*
{phone or 'N/A'}
{lead.get('address', 'N/A')}

*Message Sent:*
_{message}_
━━━━━━━━━━━━━━━━━━━━
Follow up scheduled in 48hrs if no reply
    """.strip()

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=confirmation,
        parse_mode="Markdown"
    )


async def send_outreach(lead: dict, is_followup: bool = False, followup_num: int = 1) -> bool:
    print(f"\nWriting {'follow-up #' + str(followup_num) if is_followup else 'outreach'} message for: {lead['name']}")

    message = write_outreach_message(lead, is_followup, followup_num)
    print(f"   Preview: {message[:80]}...")

    lead["draft_message"] = message

    phone = lead.get("phone", "")
    whatsapp_success = False

    if phone:
        whatsapp_success = send_whatsapp(phone, message)
    else:
        print(f"   No phone number for {lead['name']} — skipping WhatsApp")

    await notify_outreach_sent(lead, message)

    return whatsapp_success