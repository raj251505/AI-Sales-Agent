import asyncio
import re
import os
from google import genai
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from playwright.async_api import async_playwright
from datetime import datetime
from config import GEMINI_API_KEY, MAX_RESULTS_PER_QUERY, SCRAPER_DELAY_SECONDS

def generate_search_queries(business_type: str, city: str) -> list[str]:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Generate a small list of Google Maps search queries to find {business_type} businesses in {city}.
    
    Rules:
    - Cover 3 different areas of {city}
    - Format: "{business_type} in [Area] {city}"
    - Return ONLY a Python list of strings, nothing else
    - Exactly 3 queries
    """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    text = response.text.strip()

    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        list_str = text[start:end]
        queries = eval(list_str)
        queries = queries[:2]
        print(f"AI generated {len(queries)} search queries for {business_type} in {city}")
        return queries
    except Exception:
        print("AI query generation failed, using basic queries")
        return [
            f"{business_type} in {city}",
            f"{business_type} in North {city}",
            f"{business_type} in South {city}",
        ]

async def scrape_query(page, query: str) -> list[dict]:
    results = []
    print(f"\nSearching: {query}")

    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Failed to load: {e}")
        return results

    try:
        panel = page.locator('div[role="feed"]')
        for _ in range(6):
            await panel.evaluate("el => el.scrollTop += 1500")
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    cards = await page.locator('a[href*="/maps/place/"]').all()
    print(f"Found {len(cards)} listings")

    seen_names = set()

    for card in cards[:MAX_RESULTS_PER_QUERY]:
        try:
            name = await card.get_attribute("aria-label") or ""
            href = await card.get_attribute("href") or ""

            if not name or name in seen_names:
                continue
            seen_names.add(name)

            await card.click()
            await page.wait_for_timeout(2500)

            data = await extract_details(page, name, href)
            if data:
                results.append(data)
                status = "URL Found" if data["website"] else "NO WEBSITE"
                print(f"{data['name'][:40]:<40} {status}")

        except Exception:
            continue

    return results

async def extract_details(page, name: str, href: str) -> dict | None:
    try:
        data = {
            "name": name.strip(),
            "address": "",
            "phone": "",
            "website": "",
            "rating": "",
            "reviews": "",
            "hours": "",
            "maps_link": href,
            "score": 0,
            "tier": "",
            "status": "New",
            "outreach_sent": "",
            "follow_up_count": 0,
            "last_contacted": "",
        }

        await page.wait_for_timeout(1000)

        try:
            addr = page.locator('button[data-item-id="address"]')
            if await addr.count() > 0:
                data["address"] = (await addr.inner_text()).strip()
        except Exception:
            pass

        try:
            phone_btn = page.locator('button[data-item-id^="phone"]')
            if await phone_btn.count() > 0:
                data["phone"] = (await phone_btn.inner_text()).strip()
        except Exception:
            pass

        try:
            web_btn = page.locator('a[data-item-id="authority"]')
            if await web_btn.count() > 0:
                data["website"] = (await web_btn.get_attribute("href") or "").strip()
        except Exception:
            pass

        try:
            rating_el = page.locator('div.fontDisplayLarge')
            if await rating_el.count() > 0:
                data["rating"] = (await rating_el.first.inner_text()).strip()
        except Exception:
            pass

        try:
            review_el = page.locator('button[jsaction*="reviewChart"]')
            if await review_el.count() > 0:
                raw = await review_el.first.inner_text()
                nums = re.findall(r'[\d,]+', raw)
                if nums:
                    data["reviews"] = nums[0].replace(",", "")
        except Exception:
            pass

        try:
            hours_el = page.locator('div[jsaction*="openhours"]')
            if await hours_el.count() > 0:
                raw = await hours_el.first.inner_text()
                data["hours"] = raw.split("\n")[0].strip()
        except Exception:
            pass

        return data

    except Exception:
        return None

def export_to_excel(all_results: list[dict], business_type: str, city: str) -> str:
    seen = set()
    unique = []
    for r in all_results:
        key = (r["name"].lower(), r["phone"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    no_website = [r for r in unique if not r["website"]]
    has_website = [r for r in unique if r["website"]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{business_type.replace(' ', '_')}_{city}_{timestamp}.xlsx"
    output_path = os.path.join(os.path.dirname(__file__), filename)

    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "No Website (Priority)"
    write_sheet(ws1, no_website, priority=True)

    ws2 = wb.create_sheet("All Leads")
    write_sheet(ws2, unique, priority=False)

    ws3 = wb.create_sheet("Has Website")
    write_sheet(ws3, has_website, priority=False)

    wb.save(output_path)

    print(f"\nSaved: {output_path}")
    print(f"Total: {len(unique)} | No Website: {len(no_website)} | Has Website: {len(has_website)}")

    return output_path

def write_sheet(ws, data: list[dict], priority: bool = False):
    headers = ["#", "Name", "Phone", "Address", "Rating", "Reviews",
               "Hours", "Website", "Score", "Tier", "Status", "Maps Link"]

    header_fill = PatternFill("solid", fgColor="1B1B2F")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.row_dimensions[1].height = 30
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    no_web_fill = PatternFill("solid", fgColor="FFF3CD")
    alt_fill = PatternFill("solid", fgColor="F8F9FA")
    white_fill = PatternFill("solid", fgColor="FFFFFF")

    for i, lead in enumerate(data, 1):
        row = i + 1
        has_site = bool(lead["website"])
        row_fill = (white_fill if i % 2 == 0 else alt_fill) if has_site else no_web_fill

        values = [
            i, lead["name"], lead["phone"], lead["address"],
            lead["rating"], lead["reviews"], lead["hours"],
            lead["website"] or "-", lead.get("score", ""),
            lead.get("tier", ""), lead.get("status", "New"), lead["maps_link"]
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = row_fill
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = border
            ws.row_dimensions[row].height = 20

    widths = [4, 28, 15, 38, 7, 9, 18, 32, 7, 10, 10, 45]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.freeze_panes = "A2"
    ws.sheet_properties.tabColor = "E74C3C" if priority else "2ECC71"

async def run_scraper(business_type: str, city: str) -> str:
    print("=" * 60)
    print(f"  Scraping {business_type} in {city}")
    print("=" * 60)

    queries = generate_search_queries(business_type, city)
    all_results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for query in queries:
            if len(all_results) >= 10:
                print(f"Reached 10 leads, stopping early")
                break
            try:
                results = await scrape_query(page, query)
                all_results.extend(results)
                all_results = all_results[:10]   # hard cap — trim any overshoot
                if len(all_results) >= 10:
                    print(f"Reached 10 leads, stopping early")
                    break
                await page.wait_for_timeout(SCRAPER_DELAY_SECONDS * 1000)
            except Exception as e:
                print(f"Error: {e}")
                continue

        await browser.close()

    if all_results:
        return export_to_excel(all_results, business_type, city)
    else:
        print("No results found")
        return ""

if __name__ == "__main__":
    business_type = input("Business type (e.g. gym, restaurant): ").strip()
    city = input("City (e.g. Mumbai, Pune): ").strip()
    asyncio.run(run_scraper(business_type, city))