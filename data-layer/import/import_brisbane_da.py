#!/usr/bin/env python3
"""Import Brisbane development applications from Development.i portal.

Uses Playwright browser automation to download CSV exports and scrape
detail pages from the Brisbane City Council Development.i portal.

Three operating modes:

  SCRAPE  — download CSV exports from the portal search page.
            Supports full (2020 → now) or delta (last N days).
            Two application groups: Development and Building.

  ENRICH  — visit detail pages for applications already in the DB to
            fill in milestones, properties, and parsed categories.

  MONITOR — re-check active (non-terminal) applications for status
            and detail changes.

Usage:
    # Delta — last 30 days (default), both groups
    python import_brisbane_da.py

    # Full import (2020 → now, month by month)
    python import_brisbane_da.py --full

    # Specific date range
    python import_brisbane_da.py --from-date 2024-01-01 --to-date 2024-06-30

    # Single group only
    python import_brisbane_da.py --group development

    # Enrich detail data for un-enriched active applications
    python import_brisbane_da.py --enrich
    python import_brisbane_da.py --enrich --limit 50

    # Enrich a single application
    python import_brisbane_da.py --app A006987133

    # Monitor active applications for updates
    python import_brisbane_da.py --monitor
    python import_brisbane_da.py --monitor --limit 100

    # Show the browser (for debugging)
    python import_brisbane_da.py --days 7 --headed

Prerequisites:
    pip install playwright psycopg2-binary python-dotenv
    playwright install chromium
"""

import argparse
import csv
import io
import logging
import re
import time
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright, Page

from da_common import (
    USER_AGENT,
    is_terminal,
    monitoring_status_for,
    get_connection,
    month_ranges,
    parse_description,
    resolve_cadastre_lotplan,
    lookup_cadastre_suburb,
    parse_location_address,
)

log = logging.getLogger("import_brisbane_da")

# ── Constants ────────────────────────────────────────────────────────────────

BASE_URL = "https://developmenti.brisbane.qld.gov.au"
SEARCH_URL = f"{BASE_URL}/Home/MapSearch"
DETAIL_URL = f"{BASE_URL}/Home/ApplicationDetailsView"
PROPERTY_URL = f"{BASE_URL}/Home/PropertyDetailsView"

FULL_START_DATE = date(2020, 1, 1)
BATCH_SIZE = 200
DEFAULT_DELAY = 2.0

DELAY = DEFAULT_DELAY

# Application groups → filter values on the portal
GROUPS = {
    "development": {"label": "Development", "include_da": True, "include_ba": False},
    "building": {"label": "Building", "include_da": False, "include_ba": True},
}

# Brisbane milestone stage names → DB column names
STAGE_COLUMN_MAP = {
    "record creation date": "record_creation_date",
    "commence confirmation period date": "commence_confirmation_date",
    "properly made date": "properly_made_date",
    "action notice response received date": "action_notice_response_date",
    "confirmation notice sent date": "confirmation_notice_sent_date",
    "information request sent date": "info_request_sent_date",
    "final response received date": "final_response_received_date",
    "public notification compliance notice date": "public_notification_date",
    "decision notice date": "decision_notice_date",
}


_RE_DESC_ADDR = re.compile(r"^(.+?\bQLD\s+\d{4,5})", re.IGNORECASE)


def _extract_description_address(description: str) -> str | None:
    """Extract location_address from a Brisbane Full Description string.

    Format: "ADDRESS QLD POSTCODE - App Type - Applicant - date"
    Uses the QLD + postcode sentinel as a reliable end-of-address marker,
    which handles hyphenated street numbers correctly (splitting on " - " does not).

    Returns None if the sentinel is not found.
    """
    m = _RE_DESC_ADDR.search(description)
    return m.group(1).strip() if m else None


def epoch_ms_to_date(ms: int | str | None) -> date | None:
    """Convert epoch milliseconds to a date, or None if 0/empty."""
    if not ms:
        return None
    ms = int(ms)
    if ms <= 0:
        return None
    return datetime.utcfromtimestamp(ms / 1000).date()


# ── CSV scrape ───────────────────────────────────────────────────────────────

def set_filters(page: Page, group: str, from_date: date, to_date: date) -> None:
    """Set the search filters on the MapSearch page.

    The filter panel (ul#search-filters) is display:none by default on desktop.
    All filter controls are set via JavaScript to avoid visibility constraints.

    Controls discovered from page inspection:
    - ul#search-filters                — hidden panel, must force-show
    - select#filter-application-group — values: "development" / "building"
    - input#status-submitted           — radio for "Submitted" date range
    - input#dateRangeInput             — daterangepicker input
    """
    log.info(f"Setting filters: group={group}, {from_date} → {to_date}")

    # Wait for page to settle
    page.wait_for_selector("#search-filters", state="attached", timeout=20000)
    time.sleep(0.5)

    # Force the filter panel visible (it's display:none by default on desktop)
    page.evaluate("document.getElementById('search-filters').style.display = 'block'")
    time.sleep(0.5)

    # 1. Set application group (value is lowercase: "development" / "building")
    group_value = group.lower()
    page.evaluate(f"""() => {{
        const sel = document.getElementById('filter-application-group');
        sel.value = '{group_value}';
        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}""")
    time.sleep(2.0)  # wait for results to refresh after group change

    # 2. Open the date range dropdown (click the header to reveal it)
    page.evaluate("""() => {
        const dropdown = document.getElementById('date-range-dropdown');
        if (dropdown) dropdown.style.display = 'block';
    }""")
    time.sleep(0.3)

    # 3. Ensure "Submitted" radio is selected
    page.evaluate("""() => {
        const r = document.getElementById('status-submitted');
        if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true})); }
    }""")
    time.sleep(0.3)

    # 4. Set dates via the daterangepicker jQuery plugin API.
    # Note: picker format is DD/MM/YYYY with separator ' - '.
    # updateElement() doesn't work when the input is hidden, so we manually
    # set the value string and then trigger the apply event.
    from_str = from_date.strftime("%d/%m/%Y")
    to_str = to_date.strftime("%d/%m/%Y")

    set_result = page.evaluate(f"""() => {{
        try {{
            var el = document.getElementById('dateRangeInput');
            var jq = window.jQuery || window.$;
            if (!jq) return 'no jQuery';
            var picker = jq(el).data('daterangepicker');
            if (!picker) return 'no picker';
            picker.setStartDate('{from_str}');
            picker.setEndDate('{to_str}');
            var val = picker.startDate.format('DD/MM/YYYY') + picker.locale.separator + picker.endDate.format('DD/MM/YYYY');
            jq(el).val(val);
            jq(el).trigger('apply.daterangepicker', picker);
            return 'ok: ' + val;
        }} catch(e) {{ return 'error: ' + e.message; }}
    }}""")
    log.info(f"Daterangepicker set: {set_result}")
    time.sleep(DELAY)  # wait for results to refresh after date change

    # Hide the filter panel so it doesn't intercept clicks on the download button
    page.evaluate("document.getElementById('search-filters').style.display = 'none'")


def download_csv(page: Page) -> str:
    """Click the CSV download button and return the CSV content."""
    log.info("Clicking CSV download …")

    with page.expect_download(timeout=120000) as download_info:
        page.locator(".download-csv").click()

    download = download_info.value
    path = download.path()
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    log.info(f"Downloaded CSV: {len(content)} bytes")
    return content


def parse_csv(content: str) -> list:
    """Parse CSV content into a list of dicts with normalised keys."""
    reader = csv.DictReader(io.StringIO(content))
    records = []
    for row in reader:
        # Normalise column names to lowercase
        normalised = {k.strip().lower(): (v.strip() if v else None) for k, v in row.items()}
        records.append(normalised)
    return records


def map_csv_record(row: dict, group: str) -> dict | None:
    """Map a CSV row to our DB column names."""
    app_num = (
        row.get("application number")
        or row.get("app no.")
        or row.get("application")
        or row.get("number")
    )
    if not app_num:
        return None

    # Parse lodgement date — try multiple formats
    date_str = (
        row.get("date submitted")
        or row.get("lodgement date")
        or row.get("date lodged")
        or row.get("date")
    )
    lodgement_date = None
    if date_str:
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                lodgement_date = datetime.strptime(date_str.strip(), fmt).date()
                break
            except ValueError:
                continue

    description = (
        row.get("description")
        or row.get("application description")
        or row.get("proposal")
    )
    status = row.get("status") or row.get("progress")
    address = (
        row.get("address")
        or row.get("property address")
        or row.get("location")
        or row.get("primary address")
    )
    app_type = row.get("application type") or row.get("type")
    suburb = row.get("suburb") or row.get("locality")

    return {
        "application_number": app_num.strip(),
        "description": description,
        "application_type": app_type,
        "application_group": GROUPS[group]["label"],
        "lodgement_date": lodgement_date,
        "status": status,
        "suburb": suburb,
        "location_address": address,
        "monitoring_status": monitoring_status_for(status),
    }


# ── Detail page extraction ───────────────────────────────────────────────────

def _parse_rendered_date(text: str) -> date | None:
    """Parse a date rendered by Development.i JS (D/M/YYYY or DD/MM/YYYY)."""
    if not text or not text.strip():
        return None
    text = text.strip()
    for fmt in ("%d/%m/%Y",):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    # JS renders as D/M/YYYY (no leading zeros)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def extract_detail(page: Page) -> dict:
    """Extract all data from a Brisbane Development.i detail page.

    By the time Playwright reaches networkidle, the portal's JS has already
    run processDateFields() — so date-number spans contain rendered text
    (e.g. "19/2/2026") not epoch ms.  We parse dates from visible text.
    """
    out = {}

    # Helper to get text from a label/value pair
    # HTML pattern: <div class="col-sm-3"><h5>Label:</h5></div>
    #               <div class="col-sm-8"><span>Value</span></div>
    def get_field(label: str) -> str | None:
        """Find h5 with label text and return the adjacent div's value."""
        h5 = page.locator(f"h5:has-text('{label}')")
        if h5.count() == 0:
            return None
        parent = h5.first.locator("xpath=..")
        sibling = parent.locator("xpath=following-sibling::div")
        if sibling.count() > 0:
            text = sibling.first.text_content().strip()
            return text if text else None
        return None

    def get_date_field(label: str) -> date | None:
        """Get a date value from a label — parses rendered text."""
        text = get_field(label)
        return _parse_rendered_date(text)

    # -- Header fields --
    # Labels discovered from real page inspection:
    out["status"] = get_field("Progress:") or get_field("Progress Status:")
    out["decision"] = get_field("Stage/Decision:") or get_field("Decision:")
    out["application_type"] = get_field("Application Type:")
    out["assessment_level"] = get_field("Assessment Level:")
    out["use_categories"] = get_field("Use:")
    out["assessment_officer"] = get_field("Assessment Officer:")
    out["appeal_result"] = get_field("Appeal result:") or get_field("Appeal Result:")
    out["lodgement_date"] = get_date_field("Date Submitted:")

    # -- Description --
    # Full Description format: "ADDRESS - App Type - Applicant (Primary Applicant), Consultant (Consultant) - date"
    desc = get_field("Full Description:") or get_field("Description:")
    if desc:
        out["description"] = desc
        address_part = _extract_description_address(desc)
        if address_part:
            out["location_address"] = address_part

    # -- Assessment stages table --
    # Table has columns: Description | Decision | Date
    # JS has already rendered dates as text in the last cell
    stage_rows = page.locator("table.table-bordered tr")
    for i in range(stage_rows.count()):
        row = stage_rows.nth(i)
        cells = row.locator("td")
        if cells.count() < 3:
            continue

        stage_name = cells.nth(0).text_content().strip().lower()
        col_name = STAGE_COLUMN_MAP.get(stage_name)
        if not col_name:
            continue

        # Date is rendered text in the last cell (JS already ran)
        date_text = cells.nth(2).text_content().strip()
        d = _parse_rendered_date(date_text)
        if d:
            out[col_name] = d

    # -- Associated properties --
    properties = []
    prop_links = page.locator("a[href*='PropertyDetailsView?landNumber=']")
    for i in range(prop_links.count()):
        link = prop_links.nth(i)
        href = link.get_attribute("href") or ""
        m = re.search(r"landNumber=(\d+)", href)
        if m:
            land_number = m.group(1)
            address = link.text_content().strip()
            # Strip trailing date and dash separators from link text
            # Link text format: "ADDRESS - description - date"
            # We just want the address part
            if " - " in address:
                address = address.split(" - ")[0].strip()
            properties.append({
                "land_number": land_number,
                "location_address": address,
            })

    out["_properties"] = properties

    # Clean None values
    return {k: v for k, v in out.items() if v is not None}


def extract_property_lot(page: Page, land_number: str) -> dict:
    """Visit PropertyDetailsView and extract lot_on_plan and address."""
    url = f"{PROPERTY_URL}?landNumber={land_number}"
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(DELAY)

    lot_on_plan = None
    address = None

    # Look for "Lot on Plan:" label
    h5s = page.locator("h5")
    for i in range(h5s.count()):
        h5 = h5s.nth(i)
        text = h5.text_content().strip()
        parent = h5.locator("xpath=../..")
        value_div = parent.locator(".col-sm-8 span")

        if "Lot on Plan" in text and value_div.count() > 0:
            lot_on_plan = value_div.first.text_content().strip()
        elif "Address" in text and value_div.count() > 0:
            address = value_div.first.text_content().strip()

    return {
        "land_number": land_number,
        "lot_on_plan": lot_on_plan,
        "location_address": address,
    }


# ── Database operations ──────────────────────────────────────────────────────

def upsert_summary(conn, records: list) -> int:
    """INSERT … ON CONFLICT UPDATE for summary-level data."""
    if not records:
        return 0

    sql = """
        INSERT INTO brisbane_dev_applications
            (application_number, description, application_type, application_group,
             lodgement_date, status, suburb, location_address,
             monitoring_status, last_scraped_at)
        VALUES
            (%(application_number)s, %(description)s, %(application_type)s,
             %(application_group)s, %(lodgement_date)s, %(status)s,
             %(suburb)s, %(location_address)s,
             %(monitoring_status)s, NOW())
        ON CONFLICT (application_number) DO UPDATE SET
            description      = COALESCE(EXCLUDED.description, brisbane_dev_applications.description),
            application_type = COALESCE(EXCLUDED.application_type, brisbane_dev_applications.application_type),
            application_group = COALESCE(EXCLUDED.application_group, brisbane_dev_applications.application_group),
            lodgement_date   = COALESCE(EXCLUDED.lodgement_date, brisbane_dev_applications.lodgement_date),
            status           = EXCLUDED.status,
            suburb           = COALESCE(EXCLUDED.suburb, brisbane_dev_applications.suburb),
            location_address = COALESCE(EXCLUDED.location_address, brisbane_dev_applications.location_address),
            monitoring_status = EXCLUDED.monitoring_status,
            status_changed_at = CASE
                WHEN brisbane_dev_applications.status IS DISTINCT FROM EXCLUDED.status
                THEN NOW()
                ELSE brisbane_dev_applications.status_changed_at
            END,
            last_scraped_at  = NOW()
    """

    cur = conn.cursor()
    count = 0
    for rec in records:
        if not rec or not rec.get("application_number"):
            continue
        cur.execute(sql, rec)
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
        "description", "application_type",
        "status", "decision", "suburb", "location_address",
        "assessment_level", "use_categories",
        "applicant", "consultant", "assessment_officer", "appeal_result",
        "lodgement_date",
        # Brisbane milestones
        "record_creation_date", "commence_confirmation_date",
        "properly_made_date", "action_notice_response_date",
        "confirmation_notice_sent_date", "info_request_sent_date",
        "final_response_received_date", "public_notification_date",
        "decision_notice_date",
        # Parsed categories
        "development_category", "dwelling_type", "unit_count",
        "lot_split_from", "lot_split_to",
        # Parsed address
        "street_number", "street_name", "street_type",
        "unit_type", "unit_number", "unit_suffix", "postcode",
    ]
    for col in detail_columns:
        if col in detail and detail[col] is not None:
            sets.append(f"{col} = %({col})s")
            params[col] = detail[col]

    # Monitoring status from current status
    if "status" in params:
        sets.append("monitoring_status = %(monitoring_status)s")
        params["monitoring_status"] = monitoring_status_for(params.get("status"))
        sets.append(
            "status_changed_at = CASE "
            "WHEN brisbane_dev_applications.status IS DISTINCT FROM %(status)s "
            "THEN NOW() "
            "ELSE brisbane_dev_applications.status_changed_at END"
        )

    sql = f"""
        UPDATE brisbane_dev_applications
        SET {', '.join(sets)}
        WHERE application_number = %(app_num)s
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()


def upsert_da_properties(conn, application_number: str, properties: list) -> tuple:
    """Upsert property rows into brisbane_da_properties.

    Returns (primary_cadastre_lotplan, primary_suburb).
    """
    if not properties:
        return None, None

    cur = conn.cursor()
    cur.execute(
        "DELETE FROM brisbane_da_properties WHERE application_number = %s",
        (application_number,),
    )

    primary_cadastre = None
    primary_suburb = None

    # Deduplicate by land_number — keep first occurrence
    seen_land = set()
    unique_properties = []
    for prop in properties:
        ln = prop.get("land_number")
        if ln and ln in seen_land:
            continue
        if ln:
            seen_land.add(ln)
        unique_properties.append(prop)
    properties = unique_properties

    for prop in properties:
        land_number = prop.get("land_number")
        lot_on_plan = prop.get("lot_on_plan", "").strip() if prop.get("lot_on_plan") else None
        address_raw = prop.get("location_address", "").strip() if prop.get("location_address") else None

        # Determine primary: has a real street address (not empty)
        is_primary = bool(address_raw and not address_raw.upper().startswith("LOT "))

        # Resolve cadastre_lotplan from lot_on_plan
        cadastre_lp = resolve_cadastre_lotplan(conn, lot_on_plan) if lot_on_plan else None

        # Cadastre suburb
        cadastre_suburb = lookup_cadastre_suburb(cur, cadastre_lp) if cadastre_lp else None

        parsed = parse_location_address(address_raw)

        cur.execute(
            """
            INSERT INTO brisbane_da_properties
                (application_number, land_number, lot_on_plan, suburb,
                 location_address, cadastre_lotplan, is_primary,
                 cadastre_suburb, street_number, street_name, street_type,
                 unit_type, unit_number, unit_suffix, postcode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                application_number,
                land_number,
                lot_on_plan,
                parsed["suburb"],
                address_raw,
                cadastre_lp,
                is_primary,
                cadastre_suburb,
                parsed["street_number"],
                parsed["street_name"],
                parsed["street_type"],
                parsed["unit_type"],
                parsed["unit_number"],
                parsed["unit_suffix"],
                parsed["postcode"],
            ),
        )

        if is_primary and primary_cadastre is None:
            primary_cadastre = cadastre_lp
            primary_suburb = parsed["suburb"]

    conn.commit()
    cur.close()
    return primary_cadastre, primary_suburb


# ── High-level modes ─────────────────────────────────────────────────────────

def run_scrape(page: Page, conn, args) -> None:
    """Download CSV exports for each group and date range."""
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

    groups_to_scrape = (
        [args.group] if args.group else list(GROUPS.keys())
    )

    total_upserted = 0
    for group in groups_to_scrape:
        log.info(f"=== Group: {GROUPS[group]['label']} ===")
        for i, (from_d, to_d) in enumerate(ranges, 1):
            log.info(f"[{i}/{len(ranges)}] {from_d} → {to_d}")
            try:
                page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
                time.sleep(DELAY)

                set_filters(page, group, from_d, to_d)

                csv_content = download_csv(page)
                rows = parse_csv(csv_content)

                records = []
                for row in rows:
                    mapped = map_csv_record(row, group)
                    if mapped:
                        records.append(mapped)

                if records:
                    count = upsert_summary(conn, records)
                    total_upserted += count
                    log.info(f"  Upserted {count} records")
                else:
                    log.info("  No records found")
            except Exception as e:
                log.error(f"  Error scraping {group} {from_d} → {to_d}: {e}")
                continue

    log.info(f"Scrape complete. Total upserted: {total_upserted}")


def enrich_one(page: Page, conn, app_num: str, app_type: str | None) -> None:
    """Enrich a single application from its detail page."""
    url = f"{DETAIL_URL}?appNo={app_num}&type=plan_development_apps"
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(DELAY)

    # Check if we got redirected to home page (invalid app)
    if "/Home/MapSearch" in page.url or page.locator("h1:has-text('Development.i')").count() > 0:
        # Check more carefully — the home page has a search bar
        if page.locator(".search-container, #searchTerm").count() > 0:
            log.warning(f"  {app_num} redirected to home page — skipping")
            upsert_detail(conn, app_num, {})
            return

    detail = extract_detail(page)

    # Parse description into categories
    desc = detail.get("description")
    a_type = detail.get("application_type") or app_type
    parsed = parse_description(desc, a_type)
    # Only merge parsed fields that aren't already set from the detail page
    for k, v in parsed.items():
        if v is not None and detail.get(k) is None:
            detail[k] = v

    # Parse location_address into street/suburb/postcode components
    if detail.get("location_address"):
        parsed_addr = parse_location_address(detail["location_address"])
        for k, v in parsed_addr.items():
            if v is not None:
                detail.setdefault(k, v)

    # Extract and resolve properties
    raw_properties = detail.pop("_properties", [])
    enriched_properties = []

    for prop in raw_properties:
        land_number = prop["land_number"]
        prop_data = extract_property_lot(page, land_number)
        enriched_properties.append(prop_data)

        # Navigate back to detail page for next property
        if len(raw_properties) > 1:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(DELAY)

    primary_cadastre, primary_suburb = upsert_da_properties(
        conn, app_num, enriched_properties
    )
    if primary_suburb:
        detail["suburb"] = primary_suburb

    log.info(
        f"  {len(enriched_properties)} property row(s) — "
        f"primary cadastre: {primary_cadastre}"
    )

    upsert_detail(conn, app_num, detail)
    log.info(f"  Updated {len(detail)} fields")


def run_enrich(conn, args) -> None:
    """Enrich unenriched applications."""
    cur = conn.cursor()

    target_app = getattr(args, "app", None)
    if target_app:
        cur.execute(
            "SELECT application_number, application_type FROM brisbane_dev_applications "
            "WHERE application_number = %s",
            (target_app,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            log.error(f"Application '{target_app}' not found in database")
            return

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not getattr(args, "headed", False))
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(30000)
            try:
                enrich_one(page, conn, row[0], row[1])
            finally:
                browser.close()
        return

    conditions = ["detail_scraped_at IS NULL"]
    if not getattr(args, "include_closed", False):
        conditions.append("monitoring_status = 'active'")

    sql = f"""
        SELECT application_number, application_type
        FROM brisbane_dev_applications
        WHERE {' AND '.join(conditions)}
        ORDER BY lodgement_date DESC NULLS LAST
    """
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    cur.execute(sql)
    rows = [(r[0], r[1]) for r in cur.fetchall()]
    cur.close()

    log.info(f"{len(rows)} applications to enrich")
    if not rows:
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not getattr(args, "headed", False))
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(30000)
        consecutive_errors = 0

        try:
            for i, (app_num, app_type) in enumerate(rows, 1):
                try:
                    log.info(f"[{i}/{len(rows)}] {app_num}")
                    enrich_one(page, conn, app_num, app_type)
                    consecutive_errors = 0
                except Exception as e:
                    log.error(f"  Error on {app_num}: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        log.error("  5 consecutive errors — stopping")
                        break
                    try:
                        upsert_detail(conn, app_num, {})
                    except Exception as upsert_err:
                        log.warning(f"Could not mark {app_num} as failed after scrape error: {upsert_err}")
        finally:
            browser.close()


def run_monitor(conn, args) -> None:
    """Re-check active applications for status/detail changes."""
    cur = conn.cursor()
    sql = """
        SELECT application_number, application_type
        FROM brisbane_dev_applications
        WHERE monitoring_status = 'active'
        ORDER BY last_scraped_at ASC NULLS FIRST
    """
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    cur.execute(sql)
    rows = [(r[0], r[1]) for r in cur.fetchall()]
    cur.close()

    log.info(f"{len(rows)} active applications to monitor")
    if not rows:
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not getattr(args, "headed", False))
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(30000)
        updated = 0
        closed = 0
        consecutive_errors = 0

        try:
            for i, (app_num, app_type) in enumerate(rows, 1):
                try:
                    log.info(f"[{i}/{len(rows)}] {app_num}")
                    enrich_one(page, conn, app_num, app_type)
                    updated += 1
                    consecutive_errors = 0

                    # Check if now terminal
                    cur2 = conn.cursor()
                    cur2.execute(
                        "SELECT status FROM brisbane_dev_applications WHERE application_number = %s",
                        (app_num,),
                    )
                    row = cur2.fetchone()
                    cur2.close()
                    if row and is_terminal(row[0]):
                        closed += 1
                        log.info(f"  Status '{row[0]}' → closed")
                    else:
                        log.info(f"  Status '{row[0] if row else 'unknown'}' → still active")

                except Exception as e:
                    log.error(f"  Error monitoring {app_num}: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        log.error("  5 consecutive errors — stopping")
                        break
        finally:
            browser.close()

    log.info(f"Monitor complete. Updated: {updated}, newly closed: {closed}")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import Brisbane development applications from Development.i"
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true",
                      help="Full import from 2020 to now")
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
    parser.add_argument("--group", type=str, choices=list(GROUPS.keys()),
                        help="Scrape only this application group")
    parser.add_argument("--headed", action="store_true",
                        help="Show browser window for debugging")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Seconds between page loads (default {DEFAULT_DELAY})")
    parser.add_argument("--limit", type=int,
                        help="Max applications to process (--enrich / --monitor)")
    parser.add_argument("--include-closed", action="store_true",
                        help="Include closed/terminal-status apps (--enrich only)")
    parser.add_argument("--app", type=str, metavar="APP_NUMBER",
                        help="Enrich a specific application number")

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
        if args.enrich or args.app:
            run_enrich(conn, args)
        elif args.monitor:
            run_monitor(conn, args)
        else:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not args.headed)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.set_default_timeout(30000)
                try:
                    run_scrape(page, conn, args)
                finally:
                    browser.close()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
