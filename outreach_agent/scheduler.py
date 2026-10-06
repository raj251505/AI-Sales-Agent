from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from crm import get_leads_for_followup, update_lead_status
from outreach import send_outreach
from telegram_bot import send_message
from config import FOLLOW_UP_HOURS, MAX_FOLLOW_UPS

import asyncio

async def check_and_followup():
    print(f"\nScheduler check: {datetime.now().strftime('%H:%M %d %b')}")

    leads = await asyncio.to_thread(get_leads_for_followup, FOLLOW_UP_HOURS)

    if not leads:
        print("No follow ups needed right now")
        return

    print(f"{len(leads)} leads need follow up")

    for row in leads:
        try:
            lead = {
                "name": row.get("Business Name", ""),
                "phone": row.get("Phone", ""),
                "email": row.get("Email", ""),
                "address": row.get("Address", ""),
                "rating": row.get("Rating", ""),
                "reviews": row.get("Reviews", ""),
                "website": row.get("Website", ""),
            }
            lead_id = row.get("ID", "")
            followup_count = int(row.get("Follow Up Count", 0)) + 1

            print(f"- Follow up #{followup_count} for: {lead['name']}")

            await send_outreach(lead, True, followup_count)

            await asyncio.to_thread(
                update_lead_status,
                lead_id,
                "Follow Up Sent" if followup_count < MAX_FOLLOW_UPS else "Closed",
                {
                    "follow_up_count": followup_count,
                    "outreach_sent": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            )

            await send_message(
                f"Follow up #{followup_count} sent to *{lead['name']}*\n"
                f"{'Marked as Closed (max follow ups reached)' if followup_count >= MAX_FOLLOW_UPS else ''}"
            )

        except Exception as e:
            print(f"Follow up failed for {row.get('Business Name')}: {e}")

def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        check_and_followup,
        trigger=IntervalTrigger(hours=1),
        id="followup_check",
        name="Follow Up Checker",
        replace_existing=True
    )

    scheduler.start()
    print(f"Scheduler started - checking every 1 hour for follow ups")
    print(f"Follow up after: {FOLLOW_UP_HOURS} hours | Max follow ups: {MAX_FOLLOW_UPS}")

    return scheduler