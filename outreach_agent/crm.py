import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

HEADERS = [
    "ID", "Business Name", "Phone", "Email", "Address", "Rating", "Reviews",
    "Website", "Score", "Tier", "Status", "Outreach Sent", "Follow Up Count",
    "Last Contacted", "Draft Message", "Maps Link", "Date Added"
]

def get_sheet():
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"Google Sheets connection failed: {e}")
        return None

def init_sheet():
    sheet = get_sheet()
    if not sheet:
        return

    existing = sheet.row_values(1)
    if not existing:
        sheet.append_row(HEADERS)
        print("Google Sheet initialized with headers")

def log_lead(lead: dict) -> str:
    sheet = get_sheet()
    if not sheet:
        return ""

    lead_id = f"L{datetime.now().strftime('%H%M%S')}"

    row = [
        lead_id,
        lead.get("name", ""),
        lead.get("phone", ""),
        lead.get("email", ""),
        lead.get("address", ""),
        lead.get("rating", ""),
        lead.get("reviews", ""),
        lead.get("website", ""),
        lead.get("score", ""),
        lead.get("tier", ""),
        "Pending Approval",
        "",
        0,
        "",
        lead.get("draft_message", ""),
        lead.get("maps_link", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ]

    sheet.append_row(row)
    lead["crm_id"] = lead_id
    print(f"Logged to CRM: {lead_id} - {lead.get('name')}")
    return lead_id

def update_lead_status(lead_id: str, status: str, extra: dict = None):
    sheet = get_sheet()
    if not sheet:
        return

    try:
        cell = sheet.find(lead_id)
        if not cell:
            print(f"Lead {lead_id} not found in sheet")
            return

        row = cell.row
        col_map = {h: i + 1 for i, h in enumerate(HEADERS)}

        sheet.update_cell(row, col_map["Status"], status)
        sheet.update_cell(row, col_map["Last Contacted"], datetime.now().strftime("%Y-%m-%d %H:%M"))

        if extra:
            if "outreach_sent" in extra:
                sheet.update_cell(row, col_map["Outreach Sent"], extra["outreach_sent"])
            if "follow_up_count" in extra:
                sheet.update_cell(row, col_map["Follow Up Count"], extra["follow_up_count"])
            if "draft_message" in extra:
                sheet.update_cell(row, col_map["Draft Message"], extra["draft_message"])

        print(f"CRM updated: {lead_id} - {status}")

    except Exception as e:
        print(f"CRM update failed: {e}")

def get_leads_for_followup(hours_threshold: int = 48) -> list[dict]:
    sheet = get_sheet()
    if not sheet:
        return []

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=hours_threshold)

    all_rows = sheet.get_all_records()
    followup_leads = []

    for row in all_rows:
        if row.get("Status") != "Outreach Sent":
            continue
        if row.get("Follow Up Count", 0) >= 2:
            continue

        try:
            last_contact = datetime.strptime(row["Last Contacted"], "%Y-%m-%d %H:%M")
            if last_contact < cutoff:
                followup_leads.append(row)
        except Exception:
            continue

    return followup_leads

def get_pipeline_summary() -> str:
    sheet = get_sheet()
    if not sheet:
        return "Could not connect to CRM"

    all_rows = sheet.get_all_records()

    if not all_rows:
        return "Pipeline is empty"

    total = len(all_rows)
    pending = len([r for r in all_rows if r.get("Status") == "Pending Approval"])
    approved = len([r for r in all_rows if r.get("Status") == "Approved"])
    outreach_sent = len([r for r in all_rows if r.get("Status") == "Outreach Sent"])
    rejected = len([r for r in all_rows if r.get("Status") == "Rejected"])
    closed = len([r for r in all_rows if r.get("Status") == "Closed"])
    hot = len([r for r in all_rows if "Hot" in str(r.get("Tier", ""))])

    return f"""
*Pipeline Summary*

Total Leads: {total}
Hot Leads: {hot}
Pending Approval: {pending}
Approved: {approved}
Outreach Sent: {outreach_sent}
Rejected: {rejected}
Closed: {closed}

_Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}_
    """.strip()

def log_batch(leads: list[dict]) -> None:
    init_sheet()
    for lead in leads:
        log_lead(lead)
    print(f"{len(leads)} leads logged to Google Sheets")