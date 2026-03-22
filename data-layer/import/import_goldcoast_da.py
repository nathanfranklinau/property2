#!/usr/bin/env python3
"""Import Gold Coast development applications from ePathway PD Online.

Uses Playwright browser automation to scrape the Gold Coast City Council
ePathway portal for development application data.

Three operating modes:

  SCRAPE  — collect application summary data from the results table.
            Supports full (July 2017 → now) or delta (last N days).

  ENRICH  — visit detail pages for applications already in the DB to
            fill in lot-on-plan, milestones, and documents.

  MONITOR — re-check active (non-terminal) applications for status
            and detail changes.  Applications that reach a terminal
            status (Completed, Withdrawn, Refused, Lapsed, etc.) are
            automatically marked 'closed' and excluded from future
            monitor runs.

Usage:
    # Delta — last 30 days (default)
    python import_goldcoast_da.py

    # Full import (July 2017 → now, month by month)
    python import_goldcoast_da.py --full

    # Specific date range
    python import_goldcoast_da.py --from-date 2024-01-01 --to-date 2024-06-30

    # Enrich detail data for un-enriched active applications
    python import_goldcoast_da.py --enrich
    python import_goldcoast_da.py --enrich --limit 50
    python import_goldcoast_da.py --enrich --include-closed

    # Monitor active applications for updates
    python import_goldcoast_da.py --monitor
    python import_goldcoast_da.py --monitor --limit 100

    # Show the browser (for debugging)
    python import_goldcoast_da.py --days 7 --headed

Prerequisites:
    pip install playwright psycopg2-binary python-dotenv
    playwright install chromium
"""

import argparse
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

load_dotenv()

log = logging.getLogger("import_goldcoast_da")

# ── Constants ────────────────────────────────────────────────────────────────

BASE_URL = "https://cogc.cloud.infor.com/ePathway/epthprod/Web"
ENQUIRY_URL = f"{BASE_URL}/GeneralEnquiry"
LIST_URL = f"{ENQUIRY_URL}/EnquiryLists.aspx?ModuleCode=LAP"

FULL_START_DATE = date(2017, 7, 1)
BATCH_SIZE = 200
DEFAULT_DELAY = 1.5  # seconds between page navigations

# Delay between pages — overridden by --delay flag
DELAY = DEFAULT_DELAY

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# EnquiryListId for "Development applications after July 2017" on Gold Coast.
# Present in all detail page URLs:  EnquiryDetailView.aspx?Id=XXX&EnquiryListId=102
ENRICH_LIST_ID = 102

# Terminal statuses — applications in these states are "closed" and
# do not need further monitoring.  Comparison is case-insensitive.
TERMINAL_STATUSES = {
    "completed",
    "finalised",
    "decided",
    "withdrawn",
    "lapsed",
    "refused",
    "cancelled",
    "not properly made",
    "closed",
}


def is_terminal(status: str | None) -> bool:
    """Return True if this status means the application lifecycle is over."""
    if not status:
        return False
    return status.strip().lower() in TERMINAL_STATUSES


# ── Description parsing ──────────────────────────────────────────────────────

# Dwelling type patterns → (dwelling_type, development_category)
_DWELLING_PATTERNS = [
    (r"DUAL OCCUPANCY",            "Dual Occupancy",            "Residential"),
    (r"MULTIPLE DWELLING",         "Multiple Dwelling",         "Residential"),
    (r"SECONDARY DWELLING",        "Secondary Dwelling",        "Residential"),
    (r"SHORT.?TERM ACCOMM",        "Short-Term Accommodation",  "Residential"),
    (r"TOWNHOUSE",                 "Townhouse",                 "Residential"),
    (r"DWELLING HOUSE",            "Dwelling House",            "Residential"),
    (r"FAMILY ACCOMMODATION",      "Family Accommodation",      "Residential"),
    (r"CARETAKER",                 "Caretakers Accommodation",  "Residential"),
    (r"ROOMING ACCOMM",            "Rooming Accommodation",     "Residential"),
    (r"RETIREMENT|AGED CARE|RESIDENTIAL CARE", "Retirement Facility", "Residential"),
    (r"HOME.?BASED BUSINESS|BED.*BREAKFAST",   "Home Based Business", "Residential"),
    (r"CHILD.?CARE|KINDY",         "Childcare",                 "Commercial"),
    (r"FOOD|RESTAURANT|CAFE|TAKEAWAY", "Food & Drink",          "Commercial"),
    (r"TELECOMM",                  "Telecommunications",        "Infrastructure"),
    (r"OFFICE",                    "Office",                    "Commercial"),
    (r"SHOP|RETAIL",               "Shop/Retail",               "Commercial"),
    (r"WAREHOUSE|INDUSTR|FACTORY", "Industrial",                "Industrial"),
    (r"SERVICE STATION|CAR WASH",  "Automotive",                "Commercial"),
    (r"MEDICAL|HEALTH|VET",        "Health/Medical",            "Commercial"),
    (r"SPORT|RECREATION",          "Sport & Recreation",        "Commercial"),
    (r"HOTEL|MOTEL|RESORT",        "Tourist Accommodation",     "Commercial"),
    (r"SHOWROOM|DISPLAY",          "Showroom",                  "Commercial"),
    (r"OUTDOOR SALES",             "Outdoor Sales",             "Commercial"),
    (r"PLACE OF WORSHIP|CHURCH",   "Place of Worship",          "Community"),
    (r"EDUCATION|SCHOOL",          "Education",                 "Community"),
    (r"HOSPITAL",                  "Hospital",                  "Community"),
]

# OPW subtype patterns → (dwelling_type, development_category)
_OPW_PATTERNS = [
    (r"TREE WORKS PRIVATE",        "Private Tree Works",        "Infrastructure"),
    (r"TREE WORKS DEV",            "Tree Works (Development)",  "Infrastructure"),
    (r"LANDSCAP",                  "Landscaping",               "Infrastructure"),
    (r"CIVIL ENGINEERING",         "Civil Engineering",         "Infrastructure"),
    (r"GROUND LEVEL|CARPARK",      "Ground Level/Carparking",   "Infrastructure"),
    (r"PONTOON|SEAWALL|ROCK WALL|REVETMENT", "Waterfront Structure", "Waterfront"),
    (r"SEWER|WATER",               "Sewer & Water",             "Infrastructure"),
    (r"ELECTRICAL|STREET LIGHT",   "Electrical/Lighting",       "Infrastructure"),
    (r"VXO|VEHICLE ACCESS",        "Vehicle Access",            "Infrastructure"),
    (r"BUILDING WORKS|ABW",        "Associated Building Works", "Infrastructure"),
    (r"STORMWATER|DRAINAGE",       "Stormwater/Drainage",       "Infrastructure"),
]

# Unit count extraction patterns (ordered by priority)
_UNIT_COUNT_RES = [
    re.compile(r"(\d+)\s*(?:X\s*)?(?:MULTIPLE DWELLING|UNIT|TOWNHOUSE)", re.I),
    re.compile(r"(?:MULTIPLE DWELLING|UNIT|TOWNHOUSE)S?\s*(?:X\s*)?(\d+)", re.I),
    re.compile(r"\((\d+)\s*UNIT", re.I),
]

_LOT_SPLIT_RE = re.compile(r"(\d+)\s*INTO\s*(\d+)", re.I)

_ROL_SUBTYPE_PATTERNS = [
    (r"BOUNDARY REALIGNMENT",  "Boundary Realignment",  "Infrastructure"),
    (r"ROAD CLOSURE",          "Road Closure",          "Infrastructure"),
    (r"COMMUNITY TITLE",       "Community Title",       "Residential"),
    (r"FREEHOLD",              "Freehold Subdivision",  "Residential"),
    (r"STANDARD FORMAT",       "Standard Format",       "Residential"),
]


def parse_description(description: str | None, application_type: str | None) -> dict:
    """Parse a DA description into structured category fields.

    Returns dict with keys: development_category, dwelling_type, unit_count,
    lot_split_from, lot_split_to, assessment_level.
    """
    result = {
        "development_category": None,
        "dwelling_type": None,
        "unit_count": None,
        "lot_split_from": None,
        "lot_split_to": None,
        "assessment_level": None,
    }

    if not description:
        return result

    desc_upper = description.upper()
    app_type = (application_type or "").strip()

    # -- Assessment level (applies to all types) --
    if re.search(r"\bIMPACT\b", desc_upper):
        result["assessment_level"] = "Impact"
    elif re.search(r"\bCODE\b", desc_upper):
        result["assessment_level"] = "Code"

    # -- MCU: dwelling type + category --
    if app_type == "Material Change of Use" or app_type == "Combined Application":
        for pattern, dwelling, category in _DWELLING_PATTERNS:
            if re.search(pattern, desc_upper):
                result["dwelling_type"] = dwelling
                result["development_category"] = category
                break
        if not result["development_category"]:
            result["development_category"] = "Other"
        # Unit count
        for rx in _UNIT_COUNT_RES:
            m = rx.search(description)
            if m:
                count = int(m.group(1))
                if 1 < count < 10000:
                    result["unit_count"] = count
                break

    # -- ROL: lot split + subtype --
    elif app_type == "Reconfiguring a lot":
        for pattern, dwelling, category in _ROL_SUBTYPE_PATTERNS:
            if re.search(pattern, desc_upper):
                result["dwelling_type"] = dwelling
                result["development_category"] = category
                break
        if not result["development_category"]:
            result["development_category"] = "Residential"
        m = _LOT_SPLIT_RE.search(description)
        if m:
            result["lot_split_from"] = int(m.group(1))
            result["lot_split_to"] = int(m.group(2))

    # -- Operational Works / Vehicle Access --
    elif app_type in ("Operational Works", "OPW Vehicle Access Works"):
        for pattern, dwelling, category in _OPW_PATTERNS:
            if re.search(pattern, desc_upper):
                result["dwelling_type"] = dwelling
                result["development_category"] = category
                break
        if not result["development_category"]:
            result["development_category"] = "Infrastructure"

    # -- Prescribed Tidal Works --
    elif app_type == "Prescribed Tidal Works":
        result["development_category"] = "Waterfront"
        if re.search(r"PONTOON", desc_upper):
            result["dwelling_type"] = "Pontoon"
        elif re.search(r"SEAWALL|ROCK WALL|REVETMENT", desc_upper):
            result["dwelling_type"] = "Seawall/Revetment"
        else:
            result["dwelling_type"] = "Tidal Works"

    # -- Minor Change / Extension / Other --
    elif app_type in ("Minor Change", "Extension of Approval", "Other Change"):
        # Try to detect underlying type from description
        for pattern, dwelling, category in _DWELLING_PATTERNS:
            if re.search(pattern, desc_upper):
                result["dwelling_type"] = dwelling
                result["development_category"] = category
                break
        if not result["development_category"]:
            if re.search(r"RECONFIGU|ROL", desc_upper):
                result["development_category"] = "Residential"
            elif re.search(r"OPERATIONAL|OPW", desc_upper):
                result["development_category"] = "Infrastructure"
            else:
                result["development_category"] = "Other"

    # -- Everything else --
    else:
        result["development_category"] = "Other"

    return result

# ── Column-name normalisation (ePathway varies per installation) ─────────────

COLUMN_MAP = {
    # Application number
    "app no.": "application_number",
    "application": "application_number",
    "application no": "application_number",
    "application number": "application_number",
    "number": "application_number",
    "our reference": "application_number",
    # Description
    "application description": "description",
    "application proposal": "description",
    "description": "description",
    "proposal": "description",
    # Type
    "type": "application_type",
    "application type": "application_type",
    "type of application": "application_type",
    # Lodgement date
    "application date": "lodgement_date",
    "date": "lodgement_date",
    "date lodged": "lodgement_date",
    "date received": "lodgement_date",
    "date registered": "lodgement_date",
    "lodged": "lodgement_date",
    "lodge date": "lodgement_date",
    "lodgement date": "lodgement_date",
    "submitted": "lodgement_date",
    # Status
    "current status": "status",
    "status": "status",
    # Address
    "address": "location_address",
    "application location": "location_address",
    "location": "location_address",
    "location address": "location_address",
    "primary property address": "location_address",
    "property address": "location_address",
    "site address": "location_address",
    "site location": "location_address",
    "street address": "location_address",
    # Suburb
    "suburb": "suburb",
    "location suburb": "suburb",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def parse_au_date(s: str):
    """Parse DD/MM/YYYY → date, or return None."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def normalise_columns(row: dict) -> dict:
    """Map raw ePathway column headers to our DB column names."""
    result = {}
    for key, value in row.items():
        if key.startswith("_"):
            result[key] = value
            continue
        mapped = COLUMN_MAP.get(key.lower().strip())
        if mapped:
            result[mapped] = value.strip() if value else None
    return result


def month_ranges(start: date, end: date) -> list:
    """Split a date span into per-month (from, to) pairs."""
    ranges = []
    current = start
    while current <= end:
        month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if month_end > end:
            month_end = end
        ranges.append((current, month_end))
        current = month_end + timedelta(days=1)
    return ranges


# ── Browser helpers ──────────────────────────────────────────────────────────

def setup_session(page: Page) -> None:
    """Navigate through enquiry list → search page for DA after July 2017."""
    log.info("Setting up ePathway session …")
    page.goto(LIST_URL, wait_until="networkidle", timeout=60000)
    time.sleep(DELAY)

    # Select first radio button ("Development applications after July 2017")
    radios = page.locator("input[type='radio']")
    if radios.count() == 0:
        raise RuntimeError("No radio buttons found on enquiry list page")
    radios.first.check()
    log.info("Selected: Development applications after July 2017")

    # Click Next / Continue
    btn = page.locator("input[value='Next']")
    if btn.count() == 0:
        btn = page.locator("input[value='Continue']")
    btn.click()
    page.wait_for_load_state("networkidle")
    time.sleep(DELAY)
    log.info("On search page")


def click_date_tab(page: Page) -> None:
    """Click the date-range search tab."""
    labels = [
        "Lodgement Date", "Date Search", "Date Range",
        "Date Lodged", "Search by Date Range",
        "Date range search", "Search by date range",
    ]
    for label in labels:
        tab = page.locator(f"a:has-text('{label}')")
        if tab.count() > 0:
            tab.first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            log.info(f"Clicked date tab: {label}")
            return
    log.warning("Date tab not found — using default search view")


def search_by_dates(page: Page, from_date: date, to_date: date) -> None:
    """Fill date fields and submit."""
    log.info(f"Searching {from_date} → {to_date}")

    from_sel = "input[name*='FromDate' i]"
    to_sel = "input[name*='ToDate' i]"

    from_field = page.locator(from_sel)
    to_field = page.locator(to_sel)

    if from_field.count() == 0 or to_field.count() == 0:
        # Broader fallback
        from_field = page.locator("input[id*='FromDate']")
        to_field = page.locator("input[id*='ToDate']")

    from_field.first.fill("")
    from_field.first.fill(from_date.strftime("%d/%m/%Y"))
    to_field.first.fill("")
    to_field.first.fill(to_date.strftime("%d/%m/%Y"))

    page.locator("input[value='Search']").click()
    page.wait_for_load_state("networkidle")
    time.sleep(DELAY)


def get_total_pages(page: Page) -> int:
    label = page.locator("#ctl00_MainBodyContent_mPagingControl_pageNumberLabel")
    if label.count() > 0:
        text = label.text_content()
        m = re.search(r"Page\s+\d+\s+of\s+(\d+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 1


def parse_results_table(page: Page) -> list:
    """Parse the summary table on the current results page."""
    table = page.locator("table.ContentPanel")
    if table.count() == 0:
        return []

    # Headers
    header_row = table.first.locator("tr.ContentPanelHeading")
    if header_row.count() == 0:
        return []

    ths = header_row.first.locator("th")
    headers = [ths.nth(i).text_content().strip() for i in range(ths.count())]
    if not headers:
        return []

    # Data rows
    rows_loc = table.first.locator("tr.ContentPanel, tr.AlternateContentPanel")
    results = []

    for i in range(rows_loc.count()):
        row = rows_loc.nth(i)
        cells = row.locator("td")
        values = [cells.nth(j).text_content().strip() for j in range(cells.count())]

        if len(values) != len(headers):
            continue

        record = dict(zip(headers, values))

        # Capture the detail-page link and extract the numeric Id
        link = row.locator("a")
        if link.count() > 0:
            href = link.first.get_attribute("href")
            if href:
                record["_detail_url"] = href
                m = re.search(r"[?&]Id=(\d+)", href, re.IGNORECASE)
                if m:
                    record["_epathway_id"] = int(m.group(1))

        normalised = normalise_columns(record)
        if normalised.get("application_number"):
            # Promote private key to named field
            if "_epathway_id" in normalised:
                normalised["epathway_id"] = normalised.pop("_epathway_id")
            results.append(normalised)

    return results


# ── Summary scraper ──────────────────────────────────────────────────────────

def scrape_summary(page: Page, from_date: date, to_date: date) -> list:
    """Set up session, search by date range, parse all result pages."""
    setup_session(page)
    click_date_tab(page)
    search_by_dates(page, from_date, to_date)

    total_pages = get_total_pages(page)
    log.info(f"  {total_pages} page(s) of results")

    all_records = []

    # Page 1 is already loaded
    records = parse_results_table(page)
    all_records.extend(records)
    if total_pages > 1:
        log.info(f"  Page 1/{total_pages}: {len(records)} rows")

    # Remaining pages (direct GET with PageNumber)
    for n in range(2, total_pages + 1):
        page.goto(
            f"{ENQUIRY_URL}/EnquirySummaryView.aspx?PageNumber={n}",
            wait_until="networkidle",
        )
        time.sleep(DELAY)
        records = parse_results_table(page)
        all_records.extend(records)
        log.info(f"  Page {n}/{total_pages}: {len(records)} rows")

    return all_records


# ── Detail scraper ───────────────────────────────────────────────────────────

JS_EXTRACT_DETAIL = """
() => {
    const result = { fields: {}, milestones: [], documents: [], locations: [], decisions: [], officers: [] };

    // 1. td.ContentLabel → td.ContentData pairs (common ePathway detail layout)
    document.querySelectorAll('td.ContentLabel, td.LabelContent, td.LabelText').forEach(labelCell => {
        const label = labelCell.textContent.trim().replace(/:$/, '');
        const valueCell = labelCell.nextElementSibling;
        if (label && valueCell && label.length < 120) {
            const value = valueCell.textContent.trim();
            if (value) result.fields[label] = value;
        }
    });

    // 2. Generic 2-column label/value rows in any table (tr with exactly 2 tds,
    //    first td looks like a label — ends with colon or is short)
    document.querySelectorAll('tr').forEach(tr => {
        const tds = tr.querySelectorAll('td');
        if (tds.length !== 2) return;
        const label = tds[0].textContent.trim().replace(/:$/, '');
        const value = tds[1].textContent.trim();
        if (label && value && label.length < 120 && !(label in result.fields)) {
            result.fields[label] = value;
        }
    });

    // 3. Label → value pairs from <span>Label</span><span>Value</span>
    document.querySelectorAll('span').forEach(span => {
        const label = span.textContent.trim().replace(/:$/, '');
        const next = span.nextElementSibling;
        if (label && next && label.length < 120 && !(label in result.fields)) {
            const value = next.textContent.trim();
            if (value) result.fields[label] = value;
        }
    });

    // 4. Structured ContentPanel tables
    document.querySelectorAll('table.ContentPanel').forEach(table => {
        const headerRow = table.querySelector('tr.ContentPanelHeading');
        if (!headerRow) return;

        const headers = [...headerRow.querySelectorAll('th')].map(th => th.textContent.trim());
        const rows = [];

        table.querySelectorAll('tr.ContentPanel, tr.AlternateContentPanel').forEach(tr => {
            const cells = [...tr.querySelectorAll('td')].map(td => td.textContent.trim());
            const row = {};
            headers.forEach((h, i) => { if (cells[i] !== undefined) row[h] = cells[i]; });
            rows.push(row);
        });

        const joined = headers.map(h => h.toLowerCase()).join('|');

        if (joined.includes('task') || joined.includes('event')) {
            result.milestones.push(...rows);
        } else if (joined.includes('document') || joined.includes('attachment') || joined.includes('file name')) {
            result.documents.push(...rows);
        } else if (joined.includes('property address') || joined.includes('location address')
                   || joined.includes('lot') || joined.includes('title')) {
            result.locations.push(...rows);
        } else if (joined.includes('decision type') || joined.includes('decision date')
                   || joined.includes('decision authority')) {
            result.decisions.push(...rows);
        } else if (joined.includes('responsible officer')) {
            result.officers.push(...rows);
        }
    });

    return result;
}
"""


def extract_detail_data(raw: dict) -> dict:
    """Convert the JS-extracted detail dict into DB-ready column values."""
    # Normalise all field keys to lowercase for case-insensitive lookup
    fields = {k.lower(): v for k, v in raw.get("fields", {}).items()}
    milestones = raw.get("milestones", [])
    documents = raw.get("documents", [])
    decisions = raw.get("decisions", [])
    officers = raw.get("officers", [])
    # Normalise location row keys to lowercase too
    locations = [{k.lower(): v for k, v in loc.items()} for loc in raw.get("locations", [])]

    out = {}

    # --- Description ---
    for key in (
        "application description", "description", "proposal",
        "application proposal", "development description",
    ):
        val = fields.get(key, "").strip()
        if val:
            # Strip leading lines that look like status/type prefixes
            # (some ePathway pages concatenate status + type + description)
            lines = [ln.strip() for ln in val.splitlines() if ln.strip()]
            # If the first line is a known status word, drop it
            if lines and lines[0].upper() in {s.upper() for s in TERMINAL_STATUSES} | {
                "CURRENT ASSESSMENT", "INFORMATION REQUEST", "REFERRED",
                "UNDER ASSESSMENT", "APPROVED", "APPROVED IN PART",
            }:
                lines = lines[1:]
            out["description"] = " ".join(lines) if lines else val
            break

    # --- Status ---
    for key in ("current status", "status", "application status"):
        val = fields.get(key, "").strip()
        if val:
            out["status"] = val
            out["monitoring_status"] = _monitoring_status_for(val)
            break

    # --- Responsible officer ---
    if officers:
        ol = {k.lower(): v for k, v in officers[0].items()}
        officer_name = ol.get("responsible officer") or ol.get("officer") or ol.get("name")
        if officer_name and officer_name.strip():
            out["responsible_officer"] = officer_name.strip()
    # fallback from fields
    if "responsible_officer" not in out:
        for key in ("responsible officer", "officer"):
            val = fields.get(key, "").strip()
            if val:
                out["responsible_officer"] = val
                break

    # --- Location / Lot on Plan ---
    if locations:
        loc = locations[0]
        addr = (
            loc.get("property address")
            or loc.get("address")
            or loc.get("location address")
            or loc.get("formatted property address")
        )
        if addr:
            out["location_address"] = addr.strip()

        lot = loc.get("lot on plan") or loc.get("title") or loc.get("lot/plan")
        if lot:
            out["lot_on_plan"] = lot.strip()

        suburb = loc.get("location suburb") or loc.get("suburb")
        if suburb:
            out["suburb"] = suburb.strip()

    # Field-based fallbacks for location (keyed from the span/td extraction)
    for key in ("application location", "location address"):
        if key in fields and "location_address" not in out:
            out["location_address"] = fields[key]
    for key in ("lot on plan", "lot/plan", "title"):
        if key in fields and "lot_on_plan" not in out:
            out["lot_on_plan"] = fields[key]

    # --- Workflow events (all rows stored as JSONB) ---
    if milestones:
        out["workflow_events"] = json.dumps(milestones)

    # --- Milestone dates (keep the specific columns for easy querying) ---
    for m in milestones:
        ml = {k.lower(): v for k, v in m.items()}
        task_type = (
            ml.get("task/event type")
            or ml.get("task type")
            or ml.get("event type")
            or ""
        ).lower().strip()

        started = ml.get("actual started date") or ml.get("started") or ""
        completed = ml.get("actual completed date") or ml.get("completed") or ""

        if "pre-assessment" in task_type or "pre assessment" in task_type:
            out["pre_assessment_started"] = parse_au_date(started)
            out["pre_assessment_completed"] = parse_au_date(completed)
        elif "confirmation" in task_type:
            out["confirmation_notice_started"] = parse_au_date(started)
            out["confirmation_notice_completed"] = parse_au_date(completed)
        elif task_type == "decision":
            out["decision_started"] = parse_au_date(started)
            out["decision_completed"] = parse_au_date(completed)
        elif "decision - approved" in task_type or "decision-approved" in task_type or task_type == "decision approved":
            out["decision_approved_started"] = parse_au_date(started)
            out["decision_approved_completed"] = parse_au_date(completed)
        elif "issue decision" in task_type:
            out["issue_decision_started"] = parse_au_date(started)
            out["issue_decision_completed"] = parse_au_date(completed)
        elif "appeal period" in task_type or "applicant appeal" in task_type:
            out["appeal_period_started"] = parse_au_date(started)
            out["appeal_period_completed"] = parse_au_date(completed)

    # --- Decision table ---
    if decisions:
        dl = {k.lower(): v for k, v in decisions[0].items()}
        decision_type = dl.get("decision type") or dl.get("type")
        decision_date = dl.get("decision date") or dl.get("date")
        decision_auth = dl.get("decision authority") or dl.get("authority")
        if decision_type and decision_type.strip():
            out["decision_type"] = decision_type.strip()
        if decision_date:
            out["decision_date"] = parse_au_date(decision_date)
        if decision_auth and decision_auth.strip():
            out["decision_authority"] = decision_auth.strip()

    # --- Documents ---
    if documents:
        doc_names = []
        for d in documents:
            dl = {k.lower(): v for k, v in d.items()}
            name = (
                dl.get("document name")
                or dl.get("description")
                or dl.get("name")
                or dl.get("file name")
                or ""
            )
            if name.strip():
                doc_names.append(name.strip())
        if doc_names:
            out["documents_summary"] = json.dumps(doc_names)

    return out


# ── Database operations ──────────────────────────────────────────────────────

def lookup_suburb_from_cadastre(conn, lot_plan: str) -> str | None:
    """Return the locality (suburb) for a lot/plan from qld_cadastre_address."""
    if not lot_plan:
        return None
    cur = conn.cursor()
    cur.execute(
        "SELECT locality FROM qld_cadastre_address WHERE lotplan = %s LIMIT 1",
        (lot_plan,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def _monitoring_status_for(status: str | None) -> str:
    return "closed" if is_terminal(status) else "active"


def upsert_summary(conn, records: list) -> int:
    """INSERT … ON CONFLICT UPDATE for summary-level data.

    Sets monitoring_status based on the application status and records
    status_changed_at when the status actually changes.
    """
    if not records:
        return 0

    sql = """
        INSERT INTO goldcoast_dev_applications
            (application_number, description, application_type,
             lodgement_date, status, suburb, location_address,
             epathway_id, monitoring_status, last_scraped_at)
        VALUES
            (%(application_number)s, %(description)s, %(application_type)s,
             %(lodgement_date)s, %(status)s, %(suburb)s, %(location_address)s,
             %(epathway_id)s, %(monitoring_status)s, NOW())
        ON CONFLICT (application_number) DO UPDATE SET
            description      = COALESCE(EXCLUDED.description, goldcoast_dev_applications.description),
            application_type = COALESCE(EXCLUDED.application_type, goldcoast_dev_applications.application_type),
            lodgement_date   = COALESCE(EXCLUDED.lodgement_date, goldcoast_dev_applications.lodgement_date),
            status           = EXCLUDED.status,
            suburb           = EXCLUDED.suburb,
            location_address = EXCLUDED.location_address,
            epathway_id      = COALESCE(EXCLUDED.epathway_id, goldcoast_dev_applications.epathway_id),
            monitoring_status = EXCLUDED.monitoring_status,
            status_changed_at = CASE
                WHEN goldcoast_dev_applications.status IS DISTINCT FROM EXCLUDED.status
                THEN NOW()
                ELSE goldcoast_dev_applications.status_changed_at
            END,
            last_scraped_at  = NOW()
    """

    cur = conn.cursor()
    count = 0
    for rec in records:
        app_num = rec.get("application_number")
        if not app_num:
            continue

        status = rec.get("status")
        params = {
            "application_number": app_num,
            "description": rec.get("description"),
            "application_type": rec.get("application_type"),
            "lodgement_date": parse_au_date(rec.get("lodgement_date", "")),
            "status": status,
            "suburb": rec.get("suburb"),
            "location_address": rec.get("location_address"),
            "epathway_id": rec.get("epathway_id"),
            "monitoring_status": _monitoring_status_for(status),
        }
        cur.execute(sql, params)
        count += 1

        if count % BATCH_SIZE == 0:
            conn.commit()
            log.info(f"  Committed {count} rows …")

    conn.commit()
    return count


def upsert_detail(conn, application_number: str, detail: dict) -> None:
    """Update a single row with detail-page data."""
    sets = ["detail_scraped_at = NOW()", "last_scraped_at = NOW()"]
    params = {"app_num": application_number}

    detail_columns = [
        "description",
        "location_address", "lot_on_plan", "suburb",
        "responsible_officer",
        "workflow_events",
        "pre_assessment_started", "pre_assessment_completed",
        "confirmation_notice_started", "confirmation_notice_completed",
        "decision_started", "decision_completed",
        "decision_approved_started", "decision_approved_completed",
        "issue_decision_started", "issue_decision_completed",
        "appeal_period_started", "appeal_period_completed",
        "decision_type", "decision_date", "decision_authority",
        "documents_summary",
        "status", "monitoring_status",
        "development_category", "dwelling_type", "unit_count",
        "lot_split_from", "lot_split_to", "assessment_level",
    ]
    for col in detail_columns:
        if col in detail and detail[col] is not None:
            sets.append(f"{col} = %({col})s")
            params[col] = detail[col]

    # Track when status changes
    if "status" in params:
        sets.append(
            "status_changed_at = CASE "
            "WHEN goldcoast_dev_applications.status IS DISTINCT FROM %(status)s "
            "THEN NOW() "
            "ELSE goldcoast_dev_applications.status_changed_at END"
        )

    sql = f"""
        UPDATE goldcoast_dev_applications
        SET {', '.join(sets)}
        WHERE application_number = %(app_num)s
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()


# ── High-level modes ─────────────────────────────────────────────────────────

def run_scrape(page: Page, conn, args) -> None:
    """Scrape summary data (date-range search → results table)."""
    today = date.today()

    if args.from_date and args.to_date:
        from_d = date.fromisoformat(args.from_date)
        to_d = date.fromisoformat(args.to_date)
        ranges = month_ranges(from_d, to_d)
    elif args.full:
        ranges = month_ranges(FULL_START_DATE, today)
    else:
        from_d = today - timedelta(days=args.days)
        ranges = [(from_d, today)]

    total_upserted = 0
    for i, (from_d, to_d) in enumerate(ranges, 1):
        log.info(f"[{i}/{len(ranges)}] {from_d} → {to_d}")
        try:
            records = scrape_summary(page, from_d, to_d)
            if records:
                count = upsert_summary(conn, records)
                total_upserted += count
                log.info(f"  Upserted {count} records")
            else:
                log.info("  No records found")
        except Exception as e:
            log.error(f"  Error scraping {from_d} → {to_d}: {e}")
            continue

    log.info(f"Scrape complete. Total upserted: {total_upserted}")


def is_error_page(page: Page) -> bool:
    """Return True if ePathway returned its standard error page."""
    return (
        page.locator("img[src*='error.gif']").count() > 0
        or "encountered an error" in page.content().lower()
    )


def click_app_number_tab(page: Page) -> bool:
    """Click the Application number search tab. Returns True if found."""
    labels = [
        "Application number search",
        "Application Number Search",
        "Number search",
        "Application Number",
        "Licence/Application Number",
    ]
    for label in labels:
        tab = page.locator(f"a:has-text('{label}')")
        if tab.count() > 0:
            tab.first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            log.debug(f"Clicked tab: {label}")
            return True
    log.warning("Application number search tab not found")
    return False


def fill_app_number_and_search(page: Page, app_num: str) -> bool:
    """Fill the Licence/application number field and submit. Returns True on success."""
    selectors = [
        "input[name*='LicenceNumber' i]",
        "input[id*='LicenceNumber' i]",
        "input[name*='ApplicationNumber' i]",
        "input[id*='ApplicationNumber' i]",
        "input[name*='Number' i]",
    ]
    field = None
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            field = loc.first
            break
    if field is None:
        log.warning("Could not find Licence/application number input field")
        return False

    field.fill("")
    field.fill(app_num)

    search_btn = page.locator("input[value='Search']")
    if search_btn.count() == 0:
        log.warning("Could not find Search button")
        return False

    search_btn.click()
    page.wait_for_load_state("networkidle")
    time.sleep(DELAY)
    return True


def _enrich_chunk(worker_id: int, rows: list, args) -> None:
    """Enrich a partition of rows in a fully isolated browser + DB session.

    Each worker owns its own Playwright browser context and psycopg2
    connection.  Rows are pre-partitioned by the caller so there is no
    overlap between workers — no two workers ever write to the same row.
    """
    prefix = f"[W{worker_id}]"
    total = len(rows)
    conn = get_connection()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not getattr(args, "headed", True))
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            setup_session(page)
            search_page_url = page.url
            log.info(f"{prefix} Session ready — {total} records to process")

            consecutive_errors = 0

            for i, (app_num, app_type) in enumerate(rows, 1):
                try:
                    log.info(f"{prefix} [{i}/{total}] {app_num}")

                    page.goto(search_page_url, wait_until="networkidle", timeout=30000)
                    time.sleep(DELAY)

                    if "EnquirySearch.aspx" not in page.url:
                        log.warning(f"{prefix}   Session expired — re-establishing")
                        setup_session(page)
                        search_page_url = page.url

                    if not click_app_number_tab(page):
                        log.warning(f"{prefix}   Tab not found — skipping {app_num}")
                        consecutive_errors += 1
                        continue

                    if not fill_app_number_and_search(page, app_num):
                        log.warning(f"{prefix}   Search failed — skipping {app_num}")
                        consecutive_errors += 1
                        continue

                    link = page.locator(f"a:has-text('{app_num}')")
                    if link.count() == 0:
                        log.warning(f"{prefix}   No result link for {app_num} — skipping")
                        upsert_detail(conn, app_num, {})
                        consecutive_errors += 1
                        continue

                    link.first.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(DELAY)

                    if is_error_page(page):
                        log.warning(f"{prefix}   Error page — skipping {app_num}")
                        upsert_detail(conn, app_num, {})
                        consecutive_errors += 1
                        continue

                    consecutive_errors = 0

                    raw = page.evaluate(JS_EXTRACT_DETAIL)

                    if getattr(args, "debug", False) and i == 1:
                        log.info(f"{prefix} DEBUG raw:\n" + json.dumps(raw, indent=2))

                    detail = extract_detail_data(raw)
                    parsed = parse_description(detail.get("description"), app_type)
                    detail.update(parsed)

                    # Authoritative suburb from cadastre (overrides scraped suburb)
                    # Mirrors the lot_plan generated column: strip "Lot " prefix + spaces
                    lot_plan = re.sub(r"(?i)^\s*lot\s+", "", detail.get("lot_on_plan", "") or "").replace(" ", "")
                    if lot_plan:
                        cadastre_suburb = lookup_suburb_from_cadastre(conn, lot_plan)
                        if cadastre_suburb:
                            detail["suburb"] = cadastre_suburb

                    upsert_detail(conn, app_num, detail)
                    log.info(f"{prefix}   Updated {len(detail)} fields")

                except Exception as e:
                    log.error(f"{prefix}   Error on {app_num}: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        log.warning(f"{prefix}   3 consecutive errors — re-establishing session")
                        try:
                            setup_session(page)
                            search_page_url = page.url
                            consecutive_errors = 0
                        except Exception as se:
                            log.error(f"{prefix}   Could not re-establish session: {se}")
                    try:
                        upsert_detail(conn, app_num, {})
                    except Exception:
                        pass
                    continue

            log.info(f"{prefix} Enrichment complete")
        finally:
            browser.close()
            conn.close()


def run_enrich(conn, limit, include_closed=False, args=None) -> None:
    """Fetch unenriched rows then dispatch to N parallel worker sessions.

    Each worker (_enrich_chunk) owns its own browser context and DB
    connection.  Rows are partitioned by interleaving so each application
    number appears in exactly one worker's list — no data spillover.
    """
    workers = max(1, getattr(args, "workers", 2))
    cur = conn.cursor()

    # --app overrides all filters — single record, no parallelism needed
    target_app = getattr(args, "app", None)
    if target_app:
        cur.execute(
            "SELECT application_number, application_type FROM goldcoast_dev_applications "
            "WHERE application_number = %s",
            (target_app,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            log.error(f"Application '{target_app}' not found in database")
            return
        _enrich_chunk(0, [(row[0], row[1])], args)
        return

    conditions = ["detail_scraped_at IS NULL"]
    if not include_closed:
        conditions.append("monitoring_status = 'active'")

    sql = f"""
        SELECT application_number, application_type
        FROM goldcoast_dev_applications
        WHERE {' AND '.join(conditions)}
        ORDER BY lodgement_date DESC NULLS LAST
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur.execute(sql)
    rows = [(r[0], r[1]) for r in cur.fetchall()]
    cur.close()

    log.info(f"{len(rows)} applications to enrich across {workers} worker(s)")

    if not rows:
        return

    # Interleave-partition: worker i gets rows[i], rows[i+N], rows[i+2N], ...
    # This distributes the lodgement_date range evenly across workers.
    chunks = [rows[i::workers] for i in range(workers)]
    chunks = [c for c in chunks if c]  # drop empty chunks for small queues

    if len(chunks) == 1:
        _enrich_chunk(0, chunks[0], args)
    else:
        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            futures = {
                executor.submit(_enrich_chunk, i, chunk, args): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Worker {worker_id} raised unhandled exception: {e}")


def run_monitor(page: Page, conn, limit) -> None:
    """Re-check active (non-terminal) applications for status/detail changes.

    Uses the Application number search tab to look up each application, then
    reads current status from the detail page.  Applications that reach a
    terminal status are marked 'closed' and excluded from future monitor runs.
    """
    cur = conn.cursor()
    sql = """
        SELECT application_number, application_type
        FROM goldcoast_dev_applications
        WHERE monitoring_status = 'active'
        ORDER BY last_scraped_at ASC NULLS FIRST
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur.execute(sql)
    rows = [(r[0], r[1]) for r in cur.fetchall()]
    log.info(f"{len(rows)} active applications to monitor")

    setup_session(page)
    search_page_url = page.url
    consecutive_errors = 0
    updated = 0
    closed = 0

    for i, (app_num, app_type) in enumerate(rows, 1):
        try:
            log.info(f"[{i}/{len(rows)}] {app_num}")

            page.goto(search_page_url, wait_until="networkidle", timeout=30000)
            time.sleep(DELAY)

            if "EnquirySearch.aspx" not in page.url:
                log.warning("  Redirected away from search page — re-establishing session")
                setup_session(page)
                search_page_url = page.url

            if not click_app_number_tab(page):
                log.warning(f"  Application number tab not found — skipping")
                consecutive_errors += 1
                continue

            if not fill_app_number_and_search(page, app_num):
                log.warning(f"  Search failed — skipping")
                consecutive_errors += 1
                continue

            link = page.locator(f"a:has-text('{app_num}')")
            if link.count() == 0:
                log.warning(f"  No result link found for {app_num} — skipping")
                consecutive_errors += 1
                continue

            link.first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(DELAY)

            if is_error_page(page):
                log.warning(f"  Error page on detail — skipping")
                consecutive_errors += 1
                continue

            consecutive_errors = 0

            raw = page.evaluate(JS_EXTRACT_DETAIL)
            detail = extract_detail_data(raw)

            # Parse description into structured category fields
            parsed = parse_description(detail.get("description"), app_type)
            detail.update(parsed)

            upsert_detail(conn, app_num, detail)
            updated += 1

            fresh_status = detail.get("status")
            if is_terminal(fresh_status):
                closed += 1
                log.info(f"  Status '{fresh_status}' → closed")
            else:
                display_status = fresh_status or "unknown"
                log.info(f"  Status '{display_status}' → still active")

        except Exception as e:
            log.error(f"  Error monitoring {app_num}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                log.warning("  3 consecutive errors — re-establishing session")
                try:
                    setup_session(page)
                    search_page_url = page.url
                    consecutive_errors = 0
                except Exception as se:
                    log.error(f"  Could not re-establish session: {se}")
            continue

    log.info(f"Monitor complete. Updated: {updated}, newly closed: {closed}")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import Gold Coast development applications from ePathway"
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true",
                      help="Full import from July 2017 to now")
    mode.add_argument("--enrich", action="store_true",
                      help="Enrich existing records with detail-page data")
    mode.add_argument("--monitor", action="store_true",
                      help="Re-check active applications for status/detail updates")

    parser.add_argument("--days", type=int, default=30,
                        help="Delta: scrape last N days (default 30)")
    parser.add_argument("--from-date", type=str,
                        help="Start date YYYY-MM-DD (overrides --days)")
    parser.add_argument("--to-date", type=str,
                        help="End date YYYY-MM-DD")
    parser.add_argument("--headed", action="store_true",
                        help="Show browser window for debugging")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="Seconds between page loads (default 1.5)")
    parser.add_argument("--limit", type=int,
                        help="Max applications to process (--enrich / --monitor)")
    parser.add_argument("--include-closed", action="store_true",
                        help="Include closed/terminal-status apps (--enrich only)")
    parser.add_argument("--app", type=str, metavar="APP_NUMBER",
                        help="Enrich a specific application number (bypasses all filters)")
    parser.add_argument("--workers", type=int, default=2,
                        help="Parallel browser sessions for --enrich (default 2)")
    parser.add_argument("--debug", action="store_true",
                        help="Dump raw JS extraction for first record (--enrich)")

    args = parser.parse_args()

    global DELAY
    DELAY = args.delay

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    )

    conn = get_connection()
    log.info("Connected to database")

    try:
        if args.enrich:
            # run_enrich manages its own browser sessions per worker
            run_enrich(conn, args.limit, include_closed=args.include_closed, args=args)
        else:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not args.headed)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.set_default_timeout(30000)
                try:
                    if args.monitor:
                        run_monitor(page, conn, args.limit)
                    else:
                        run_scrape(page, conn, args)
                finally:
                    browser.close()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
