import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def send_lead_notification(lead: dict) -> None:
    async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
        tier_text = "Hot" if lead["score"] >= 7 else "Warm"
        website_status = "No Website" if not lead["website"] else f"URL: {lead['website'][:40]}"

        message = f"""
*NEW LEAD - Score: {lead['score']}/10*

*{lead['name']}*
{lead.get('address', 'N/A')}
{lead.get('phone', 'N/A')}
Rating: {lead.get('rating', 'N/A')} | {lead.get('reviews', '0')} reviews
{website_status}
{lead.get('hours', 'N/A')}

*Tier: {lead['tier']}*
_{lead.get('score_reasons', '')}_

[View on Maps]({lead.get('maps_link', '')})

Reply with:
/approve\\_{lead['_id']}
/reject\\_{lead['_id']}
        """.strip()

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
        print(f"Telegram notification sent for: {lead['name']}")

async def send_message(text: str) -> None:
    async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown"
        )

class ApprovalHandler:
    def __init__(self, on_approve, on_reject):
        self.on_approve = on_approve
        self.on_reject = on_reject
        self.app = None

    async def start(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        self.app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^/approve_'),
            self._handle_approve
        ))
        self.app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^/reject_'),
            self._handle_reject
        ))
        self.app.add_handler(CommandHandler("status", self._handle_status))
        self.app.add_handler(CommandHandler("pipeline", self._handle_status))

        print("Telegram bot listening for approvals...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        try:
             await asyncio.Event().wait()
        except KeyboardInterrupt:
             await self.app.updater.stop()
             await self.app.stop()
             await self.app.shutdown()

    async def _handle_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        lead_id = text.replace("/approve_", "").strip()

        await update.message.reply_text(f"Approved! Sending outreach for lead {lead_id}...")
        await self.on_approve(lead_id)

    async def _handle_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        lead_id = text.replace("/reject_", "").strip()

        await update.message.reply_text(f"Rejected. Lead {lead_id} skipped.")
        await self.on_reject(lead_id)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from crm import get_pipeline_summary
        summary = await asyncio.to_thread(get_pipeline_summary)
        await update.message.reply_text(summary, parse_mode="Markdown")

async def notify_batch(leads: list[dict]) -> None:
    actionable_leads = [l for l in leads if l["score"] >= 4]

    if not actionable_leads:
        await send_message("No actionable leads found in this batch.")
        return

    hot = len([l for l in actionable_leads if l["score"] >= 7])
    warm = len(actionable_leads) - hot
    await send_message(f"*{len(actionable_leads)} leads found!* ({hot} hot, {warm} warm) Sending details...")

    for i, lead in enumerate(actionable_leads):
        lead["_id"] = str(i)
        await send_lead_notification(lead)
        await asyncio.sleep(1)