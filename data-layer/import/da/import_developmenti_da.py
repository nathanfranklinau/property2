#!/usr/bin/env python3
"""Generic import script for Development.i council portals.

All QLD councils running the Development.i platform share the same page
structure, CSV download mechanism, and detail/property page layout.
This script is parameterised by a council configuration dict so the same
code handles Ipswich, Redland, Sunshine Coast, Toowoomba, and Western Downs.

Three operating modes (identical to the Brisbane importer):

  SCRAPE  — download CSV exports from the portal search page.
            Supports full or delta (last N days).

  ENRICH  — visit detail pages for applications already in the DB to
            fill in milestones, properties, and parsed categories.

  MONITOR — re-check active (non-terminal) applications for status
            and detail changes.

Usage (via per-council wrapper scripts):
    python import_ipswich_da.py                    # delta 30 days
    python import_ipswich_da.py --full             # full import
    python import_ipswich_da.py --enrich           # enrich unenriched
    python import_ipswich_da.py --enrich --workers 4
    python import_ipswich_da.py --monitor          # re-check active

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import TypedDict

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

log = logging.getLogger(__name__)

# ── Council configuration type ────────────────────────────────────────────────

class CouncilConfig(TypedDict):
    """Per-council configuration for the Development.i import."""
    name: str                   # Human-readable name, e.g. "Ipswich"
    slug: str                   # Short identifier, e.g. "ipswich"
    base_url: str               # Portal base URL (no trailing slash)
    parent_table: str           # DB table for applications
    child_table: str            # DB table for properties
    full_start_date: str        # ISO date string for --full start
    groups: dict                # Application group configs
    filter_panel_selector: str  # CSS selector for the filter panel
    filter_panel_needs_show: bool   # True if panel is hidden by default and must be forced visible
    date_input_selector: str    # CSS selector for the daterangepicker input
    group_select_id: str        # ID of the application group <select>
    detail_param: str           # Query parameter name for detail page (e.g. id, appNo, ApplicationId)
    has_detail_pages: bool      # False if portal uses AJAX modals only (no standalone detail pages)
    description_addr_at_end: bool   # True if address appears at END of description (Toowoomba format)
    ignore_https_errors: bool   # True for portals with expired SSL certs (e.g. Western Downs)


# ── Council configurations ────────────────────────────────────────────────────

# Group presets — councils vary in which application groups they expose
_GROUPS_DA_ONLY = {
    "development": {"label": "Development", "include_da": True, "include_ba": False, "include_plumb": False},
}

_GROUPS_DA_BA_PLUMB = {
    "development": {"label": "Development", "include_da": True, "include_ba": False, "include_plumb": False},
    "building": {"label": "Building", "include_da": False, "include_ba": True, "include_plumb": False},
    "plumbing": {"label": "Plumbing", "include_da": False, "include_ba": False, "include_plumb": True},
}

COUNCILS: dict[str, CouncilConfig] = {
    "ipswich": {
        "name": "Ipswich",
        "slug": "ipswich",
        "base_url": "https://developmenti.ipswich.qld.gov.au",
        "parent_table": "ipswich_dev_applications",
        "child_table": "ipswich_da_properties",
        "full_start_date": "2018-01-01",
        "groups": _GROUPS_DA_ONLY,
        "filter_panel_selector": "#search-filters",
        "filter_panel_needs_show": True,
        "date_input_selector": "#dateRangeInput",
        "group_select_id": "filter-application-group",
        # Detail page uses ?type=plan_development_apps&id=APP_NUMBER
        "detail_param": "id",
        "has_detail_pages": True,
        "description_addr_at_end": False,
        "ignore_https_errors": False,
    },
    "redland": {
        "name": "Redland",
        "slug": "redland",
        "base_url": "https://developmenti.redland.qld.gov.au",
        "parent_table": "redland_dev_applications",
        "child_table": "redland_da_properties",
        "full_start_date": "2020-01-01",
        "groups": _GROUPS_DA_BA_PLUMB,
        # Redland uses div#filter-container, which is not hidden by default
        "filter_panel_selector": "#filter-container",
        "filter_panel_needs_show": False,
        "date_input_selector": "input[name='daterange']",
        "group_select_id": "filter-application-group",
        "detail_param": "applicationNumber",
        "has_detail_pages": True,
        "description_addr_at_end": False,
        "ignore_https_errors": False,
    },
    "sunshinecoast": {
        "name": "Sunshine Coast",
        "slug": "sunshinecoast",
        "base_url": "https://developmenti.sunshinecoast.qld.gov.au",
        "parent_table": "sunshinecoast_dev_applications",
        "child_table": "sunshinecoast_da_properties",
        "full_start_date": "2020-01-01",
        "groups": _GROUPS_DA_BA_PLUMB,
        "filter_panel_selector": "#search-filters",
        "filter_panel_needs_show": True,
        "date_input_selector": "#dateRangeInput",
        "group_select_id": "filter-application-group",
        # Sunshine Coast uses ?ApplicationId= (capital A)
        "detail_param": "ApplicationId",
        "has_detail_pages": True,
        "description_addr_at_end": False,
        "ignore_https_errors": False,
    },
    "toowoomba": {
        "name": "Toowoomba",
        "slug": "toowoomba",
        "base_url": "https://developmenti.tr.qld.gov.au",
        "parent_table": "toowoomba_dev_applications",
        "child_table": "toowoomba_da_properties",
        "full_start_date": "1998-01-01",
        "groups": _GROUPS_DA_ONLY,
        "filter_panel_selector": "#search-filters",
        "filter_panel_needs_show": True,
        "date_input_selector": "#dateRangeInput",
        "group_select_id": "filter-application-group",
        "detail_param": "id",
        "has_detail_pages": True,
        # Toowoomba description format: "Proposal - ADDRESS SUBURB QLD POSTCODE"
        # Address is at the END, not the start (opposite to Brisbane).
        "description_addr_at_end": True,
        "ignore_https_errors": False,
    },
    "westerndowns": {
        "name": "Western Downs",
        "slug": "westerndowns",
        "base_url": "https://developmenti.wdrc.qld.gov.au",
        "parent_table": "westerndowns_dev_applications",
        "child_table": "westerndowns_da_properties",
        "full_start_date": "2017-01-01",
        "groups": _GROUPS_DA_ONLY,
        # Filter panel is visible by default on WDRC — no force-show needed
        "filter_panel_selector": "#search-filters",
        "filter_panel_needs_show": False,
        "date_input_selector": "#dateRangeInput",
        "group_select_id": "filter-application-group",
        "detail_param": "id",
        # WDRC uses AJAX modals only — no standalone ApplicationDetailsView.
        # Enrichment falls back to the /Geo/GetApplicationById JSON API.
        "has_detail_pages": False,
        "description_addr_at_end": False,
        # SSL certificate is expired — suppress cert validation errors.
        "ignore_https_errors": True,
    },
}


# ── Constants ────────────────────────────────────────────────────────────────

BATCH_SIZE = 200
DEFAULT_DELAY = 2.0

# Module-level delay — overridden by --delay flag
DELAY = DEFAULT_DELAY

# Development.i milestone stage names → DB column names
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


# ── URL helpers ──────────────────────────────────────────────────────────────

def search_url(cfg: CouncilConfig) -> str:
    return f"{cfg['base_url']}/Home/MapSearch"


def detail_url(cfg: CouncilConfig) -> str:
    return f"{cfg['base_url']}/Home/ApplicationDetailsView"


def property_url(cfg: CouncilConfig) -> str:
    return f"{cfg['base_url']}/Home/PropertyDetailsView"


# ── Address extraction ───────────────────────────────────────────────────────

_RE_DESC_ADDR_START = re.compile(r"^(.+?\bQLD\s+\d{4,5})", re.IGNORECASE)
# Toowoomba format: "Description - ADDRESS SUBURB QLD POSTCODE"
# Address starts with a street number (digit, optionally followed by digit/letter/hyphen)
# then a space, then the street name. We find the LAST occurrence of a
# number-prefixed address segment that ends with QLD POSTCODE.
_RE_DESC_ADDR_END = re.compile(r" - (\d[\d\w/-]*\s+.+?\bQLD\s+\d{4,5})\s*$", re.IGNORECASE)


def _extract_description_address(description: str, addr_at_end: bool = False) -> str | None:
    """Extract location_address from a Development.i Full Description string.

    addr_at_end=False (default): "ADDRESS QLD POSTCODE - App Type - ..."
    addr_at_end=True (Toowoomba): "Description - ADDRESS SUBURB QLD POSTCODE"
    """
    if addr_at_end:
        m = _RE_DESC_ADDR_END.search(description)
    else:
        m = _RE_DESC_ADDR_START.search(description)
    return m.group(1).strip() if m else None


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
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


# ── CSV scrape ───────────────────────────────────────────────────────────────

def _dismiss_error_dialog(page: Page) -> bool:
    """Dismiss the 'Error contacting server' modal if visible."""
    try:
        ok_btn = page.locator(".modal-footer button:has-text('OK')")
        if ok_btn.count() > 0 and ok_btn.first.is_visible(timeout=500):
            ok_btn.first.click()
            log.warning("Dismissed 'Error contacting server' dialog")
            time.sleep(0.5)
            return True
    except Exception:
        pass
    return False


def set_filters(
    page: Page,
    cfg: CouncilConfig,
    group: str,
    from_date: date,
    to_date: date,
) -> None:
    """Set the search filters on the MapSearch page."""
    log.info(f"Setting filters: group={group}, {from_date} → {to_date}")

    panel_sel = cfg["filter_panel_selector"]

    # Wait for filter panel to exist in DOM
    page.wait_for_selector(panel_sel, state="attached", timeout=20000)
    time.sleep(0.5)

    # Some portals (Brisbane, Ipswich, Sunshine Coast, Toowoomba) hide the
    # filter panel on desktop and require a JS force-show before interacting.
    # Others (Redland, Western Downs) leave it visible — no action needed.
    if cfg["filter_panel_needs_show"]:
        page.evaluate(f"""
            document.querySelector('{panel_sel}').style.display = 'block';
        """)
        time.sleep(0.5)

    # 1. Set application group
    group_id = cfg["group_select_id"]
    group_value = group.lower()
    page.evaluate(f"""() => {{
        const sel = document.getElementById('{group_id}');
        if (sel) {{
            sel.value = '{group_value}';
            sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }}""")
    time.sleep(2.0)

    # 2. Open date range dropdown if it exists
    page.evaluate("""() => {
        const dropdown = document.getElementById('date-range-dropdown');
        if (dropdown) dropdown.style.display = 'block';
    }""")
    time.sleep(0.3)

    # 3. Select "Submitted" radio if present
    page.evaluate("""() => {
        const r = document.getElementById('status-submitted');
        if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true})); }
    }""")
    time.sleep(0.3)

    # 4. Set date range via daterangepicker jQuery plugin
    from_str = from_date.strftime("%d/%m/%Y")
    to_str = to_date.strftime("%d/%m/%Y")
    date_sel = cfg["date_input_selector"]

    # Escape single quotes so the selector can be safely embedded in JS
    date_sel_js = date_sel.replace("'", "\\'")
    set_result = page.evaluate(f"""() => {{
        try {{
            var jq = window.jQuery || window.$;
            if (!jq) return 'no jQuery';
            var el = jq('{date_sel_js}')[0];
            if (!el) return 'no date input';
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
    time.sleep(DELAY)

    _dismiss_error_dialog(page)

    # Re-hide the filter panel (only if we forced it visible) so it doesn't
    # intercept clicks on the CSV download button.
    if cfg["filter_panel_needs_show"]:
        page.evaluate(f"""
            document.querySelector('{panel_sel}').style.display = 'none';
        """)


def download_csv(page: Page) -> str:
    """Click the CSV download button and return the CSV content."""
    _dismiss_error_dialog(page)
    log.info("Clicking CSV download …")

    with page.expect_download(timeout=120000) as download_info:
        page.locator(".download-csv").click()

    download = download_info.value
    path = download.path()
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    log.info(f"Downloaded CSV: {len(content)} bytes")
    return content


def parse_csv(content: str) -> list[dict]:
    """Parse CSV content into a list of dicts with normalised keys."""
    reader = csv.DictReader(io.StringIO(content))
    records = []
    for row in reader:
        normalised = {
            k.strip().lower(): (v.strip() if v else None)
            for k, v in row.items()
            if k is not None  # trailing commas in CSV create None keys
        }
        records.append(normalised)
    return records


def map_csv_record(row: dict, group: str, groups_cfg: dict) -> dict | None:
    """Map a CSV row to our DB column names.

    Development.i CSV columns vary slightly between councils but the
    core fields are consistent. We try multiple column name variants.
    """
    app_num = (
        row.get("application number")
        or row.get("app no.")
        or row.get("application")
        or row.get("number")
    )
    if not app_num:
        return None

    date_str = (
        row.get("date submitted")
        or row.get("lodgement date")
        or row.get("date lodged")
        or row.get("date")
        or row.get("date received")
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
        or row.get("full description")
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

    # Some portals include these in CSV; extract if available
    decision = row.get("stage/decision") or row.get("decision")
    assessment_level = row.get("assessment level")

    # If no separate address column, try extracting from description.
    # Pass addr_at_end=False here — CSV scrape has no config context.
    # Councils where address is at end (Toowoomba) still provide the address
    # embedded in the description; enrichment will refine it from the detail page.
    if not address and description:
        address = _extract_description_address(description, addr_at_end=False)

    # Prefer application_group from CSV if present (Ipswich includes it)
    csv_group = row.get("application group")
    group_label = csv_group if csv_group else groups_cfg[group]["label"]

    return {
        "application_number": app_num.strip(),
        "description": description,
        "application_type": app_type,
        "application_group": group_label,
        "lodgement_date": lodgement_date,
        "status": status,
        "decision": decision,
        "assessment_level": assessment_level,
        "suburb": suburb,
        "location_address": address,
        "monitoring_status": monitoring_status_for(status),
    }


# ── Detail page extraction ───────────────────────────────────────────────────

def extract_detail(page: Page) -> dict:
    """Extract all data from a Development.i detail page."""
    out = {}

    def get_field(label: str) -> str | None:
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
        text = get_field(label)
        return _parse_rendered_date(text)

    out["status"] = get_field("Progress:") or get_field("Progress Status:")
    out["decision"] = get_field("Stage/Decision:") or get_field("Decision:")
    out["application_type"] = get_field("Application Type:")
    out["assessment_level"] = get_field("Assessment Level:")
    out["use_categories"] = get_field("Use:")
    out["assessment_officer"] = get_field("Assessment Officer:")
    out["appeal_result"] = get_field("Appeal result:") or get_field("Appeal Result:")
    out["lodgement_date"] = get_date_field("Date Submitted:") or get_date_field("Date Received:")

    desc = get_field("Full Description:") or get_field("Description:")
    if desc:
        out["description"] = desc
        address_part = _extract_description_address(desc)
        if address_part:
            out["location_address"] = address_part

    # Assessment stages table
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
        date_text = cells.nth(2).text_content().strip()
        d = _parse_rendered_date(date_text)
        if d:
            out[col_name] = d

    # Associated properties
    properties = []
    prop_links = page.locator("a[href*='PropertyDetailsView?landNumber=']")
    for i in range(prop_links.count()):
        link = prop_links.nth(i)
        href = link.get_attribute("href") or ""
        m = re.search(r"landNumber=(\d+)", href)
        if m:
            land_number = m.group(1)
            address = link.text_content().strip()
            if " - " in address:
                address = address.split(" - ")[0].strip()
            properties.append({
                "land_number": land_number,
                "location_address": address,
            })

    out["_properties"] = properties
    return {k: v for k, v in out.items() if v is not None}


def extract_property_lot(page: Page, cfg: CouncilConfig, land_number: str) -> dict:
    """Visit PropertyDetailsView and extract lot_on_plan and address."""
    url = f"{property_url(cfg)}?landNumber={land_number}"
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(DELAY)

    lot_on_plan = None
    address = None

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

def upsert_summary(conn, cfg: CouncilConfig, records: list[dict]) -> int:
    """INSERT … ON CONFLICT UPDATE for summary-level data."""
    if not records:
        return 0

    table = cfg["parent_table"]
    sql = f"""
        INSERT INTO {table}
            (application_number, description, application_type, application_group,
             lodgement_date, status, suburb, location_address,
             monitoring_status, last_scraped_at)
        VALUES
            (%(application_number)s, %(description)s, %(application_type)s,
             %(application_group)s, %(lodgement_date)s, %(status)s,
             %(suburb)s, %(location_address)s,
             %(monitoring_status)s, NOW())
        ON CONFLICT (application_number) DO UPDATE SET
            description      = COALESCE(EXCLUDED.description, {table}.description),
            application_type = COALESCE(EXCLUDED.application_type, {table}.application_type),
            application_group = COALESCE(EXCLUDED.application_group, {table}.application_group),
            lodgement_date   = COALESCE(EXCLUDED.lodgement_date, {table}.lodgement_date),
            status           = EXCLUDED.status,
            suburb           = COALESCE(EXCLUDED.suburb, {table}.suburb),
            location_address = COALESCE(EXCLUDED.location_address, {table}.location_address),
            monitoring_status = EXCLUDED.monitoring_status,
            status_changed_at = CASE
                WHEN {table}.status IS DISTINCT FROM EXCLUDED.status
                THEN NOW()
                ELSE {table}.status_changed_at
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


def upsert_detail(conn, cfg: CouncilConfig, application_number: str, detail: dict) -> None:
    """Update a single row with detail-page data."""
    table = cfg["parent_table"]
    sets = ["detail_scraped_at = NOW()", "last_scraped_at = NOW()"]
    params: dict = {"app_num": application_number}

    detail_columns = [
        "description", "application_type",
        "status", "decision", "suburb", "location_address",
        "assessment_level", "use_categories",
        "applicant", "consultant", "assessment_officer", "appeal_result",
        "lodgement_date",
        # Milestones
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

    if "status" in params:
        sets.append("monitoring_status = %(monitoring_status)s")
        params["monitoring_status"] = monitoring_status_for(params.get("status"))
        sets.append(
            f"status_changed_at = CASE "
            f"WHEN {table}.status IS DISTINCT FROM %(status)s "
            f"THEN NOW() "
            f"ELSE {table}.status_changed_at END"
        )

    sql = f"""
        UPDATE {table}
        SET {', '.join(sets)}
        WHERE application_number = %(app_num)s
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()


def upsert_da_properties(
    conn,
    cfg: CouncilConfig,
    application_number: str,
    properties: list[dict],
) -> tuple[str | None, str | None]:
    """Upsert property rows into the child table.

    Returns (primary_cadastre_lotplan, primary_suburb).
    """
    if not properties:
        return None, None

    child_table = cfg["child_table"]
    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM {child_table} WHERE application_number = %s",
        (application_number,),
    )

    primary_cadastre = None
    primary_suburb = None

    # Deduplicate by land_number
    seen_land: set[str] = set()
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

        is_primary = bool(address_raw and not address_raw.upper().startswith("LOT "))

        cadastre_lp = resolve_cadastre_lotplan(conn, lot_on_plan) if lot_on_plan else None
        cadastre_suburb = lookup_cadastre_suburb(cur, cadastre_lp) if cadastre_lp else None

        parsed = parse_location_address(address_raw)

        cur.execute(
            f"""
            INSERT INTO {child_table}
                (application_number, land_number, lot_on_plan, suburb,
                 location_address, cadastre_lotplan, is_primary,
                 cadastre_suburb, street_number, street_name, street_type,
                 unit_type, unit_number, unit_suffix)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            ),
        )

        if is_primary and primary_cadastre is None:
            primary_cadastre = cadastre_lp
            primary_suburb = parsed["suburb"]

    conn.commit()
    cur.close()
    return primary_cadastre, primary_suburb


# ── High-level modes ─────────────────────────────────────────────────────────

def run_scrape(page: Page, conn, cfg: CouncilConfig, args) -> None:
    """Download CSV exports for each group and date range."""
    today = date.today()
    full_start = date.fromisoformat(cfg["full_start_date"])

    if args.from_date and args.to_date:
        from_d = date.fromisoformat(args.from_date)
        to_d = min(date.fromisoformat(args.to_date), today)
        ranges = month_ranges(from_d, to_d)
    elif args.full:
        ranges = month_ranges(full_start, today)
    else:
        from_d = today - timedelta(days=args.days)
        ranges = [(from_d, today)]

    groups_cfg = cfg["groups"]
    groups_to_scrape = (
        [args.group] if args.group else list(groups_cfg.keys())
    )

    total_upserted = 0
    for group in groups_to_scrape:
        log.info(f"=== Group: {groups_cfg[group]['label']} ===")
        for i, (from_d, to_d) in enumerate(ranges, 1):
            log.info(f"[{i}/{len(ranges)}] {from_d} → {to_d}")
            try:
                page.goto(search_url(cfg), wait_until="networkidle", timeout=60000)
                time.sleep(DELAY)

                set_filters(page, cfg, group, from_d, to_d)

                if page.locator("text=No results found").count() > 0:
                    log.info("  No results — skipping download")
                    continue

                csv_content = download_csv(page)
                rows = parse_csv(csv_content)

                records = []
                for row in rows:
                    mapped = map_csv_record(row, group, groups_cfg)
                    if mapped:
                        records.append(mapped)

                if records:
                    count = upsert_summary(conn, cfg, records)
                    total_upserted += count
                    log.info(f"  Upserted {count} records")
                else:
                    log.info("  No records found")
            except Exception as e:
                log.error(f"  Error scraping {group} {from_d} → {to_d}: {e}")
                continue

    log.info(f"Scrape complete. Total upserted: {total_upserted}")


def _enrich_via_json_api(page: Page, conn, cfg: CouncilConfig, app_num: str, app_type: str | None) -> None:
    """Enrich via the /Geo/GetApplicationById JSON API.

    Used for portals where ApplicationDetailsView returns 500 without
    a prior browser session (e.g. Western Downs). The JSON API returns
    structured data directly.
    """
    api_url = f"{cfg['base_url']}/Geo/GetApplicationById?applicationId={app_num}&appType=development"
    response = page.evaluate(f"""async () => {{
        try {{
            const resp = await fetch('{api_url}');
            if (!resp.ok) return {{ error: resp.status }};
            return await resp.json();
        }} catch(e) {{ return {{ error: e.message }}; }}
    }}""")

    if not response or response.get("error"):
        log.warning(f"  {app_num} JSON API returned error: {response}")
        upsert_detail(conn, cfg, app_num, {})
        return

    detail: dict = {}
    detail["status"] = response.get("progress")
    detail["decision"] = response.get("stage")
    detail["application_type"] = response.get("applicationType")
    detail["assessment_level"] = response.get("assessmentLevel")
    detail["description"] = response.get("description")
    detail["use_categories"] = response.get("useLevel1")

    # Parse date fields from epoch ms
    for json_key, db_col in [
        ("dateReceived", "lodgement_date"),
        ("dateDecided", "decision_notice_date"),
    ]:
        ms = response.get(json_key)
        if ms and isinstance(ms, (int, float)) and ms > 0:
            detail[db_col] = datetime.utcfromtimestamp(ms / 1000).date()

    # Extract address from description if present
    desc = detail.get("description")
    if desc:
        addr = _extract_description_address(desc, cfg["description_addr_at_end"])
        if addr:
            detail["location_address"] = addr

    # Parse description into categories
    a_type = detail.get("application_type") or app_type
    parsed = parse_description(desc, a_type)
    for k, v in parsed.items():
        if v is not None and detail.get(k) is None:
            detail[k] = v

    if detail.get("location_address"):
        parsed_addr = parse_location_address(detail["location_address"])
        for k, v in parsed_addr.items():
            if v is not None:
                detail.setdefault(k, v)

    # Associated properties from JSON
    properties = response.get("associatedProperties", [])
    enriched_properties = []
    for prop in properties:
        enriched_properties.append({
            "land_number": str(prop.get("landNumber", "")),
            "lot_on_plan": prop.get("lotPlan"),
            "location_address": prop.get("address"),
        })

    primary_cadastre, primary_suburb = upsert_da_properties(
        conn, cfg, app_num, enriched_properties
    )
    if primary_suburb:
        detail["suburb"] = primary_suburb

    # Remove None values
    detail = {k: v for k, v in detail.items() if v is not None}

    log.info(
        f"  {len(enriched_properties)} property row(s) — "
        f"primary cadastre: {primary_cadastre}"
    )

    upsert_detail(conn, cfg, app_num, detail)
    log.info(f"  Updated {len(detail)} fields (JSON API)")


def enrich_one(page: Page, conn, cfg: CouncilConfig, app_num: str, app_type: str | None) -> None:
    """Enrich a single application from its detail page or JSON API."""
    if not cfg["has_detail_pages"]:
        _enrich_via_json_api(page, conn, cfg, app_num, app_type)
        return

    param = cfg["detail_param"]
    url = f"{detail_url(cfg)}?{param}={app_num}&type=plan_development_apps"
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(DELAY)

    # Check if redirected to home page (invalid app)
    if "/Home/MapSearch" in page.url or page.locator("h1:has-text('Development.i')").count() > 0:
        if page.locator(".search-container, #searchTerm").count() > 0:
            log.warning(f"  {app_num} redirected to home page — skipping")
            upsert_detail(conn, cfg, app_num, {})
            return

    detail = extract_detail(page)

    # For portals where address is embedded at end of description, extract it.
    if cfg["description_addr_at_end"] and not detail.get("location_address"):
        desc_for_addr = detail.get("description")
        if desc_for_addr:
            extracted = _extract_description_address(desc_for_addr, addr_at_end=True)
            if extracted:
                detail["location_address"] = extracted

    # Parse description into categories
    desc = detail.get("description")
    a_type = detail.get("application_type") or app_type
    parsed = parse_description(desc, a_type)
    for k, v in parsed.items():
        if v is not None and detail.get(k) is None:
            detail[k] = v

    # Parse location_address
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
        prop_data = extract_property_lot(page, cfg, land_number)
        enriched_properties.append(prop_data)

        if len(raw_properties) > 1:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(DELAY)

    primary_cadastre, primary_suburb = upsert_da_properties(
        conn, cfg, app_num, enriched_properties
    )
    if primary_suburb:
        detail["suburb"] = primary_suburb

    log.info(
        f"  {len(enriched_properties)} property row(s) — "
        f"primary cadastre: {primary_cadastre}"
    )

    upsert_detail(conn, cfg, app_num, detail)
    log.info(f"  Updated {len(detail)} fields")


def _enrich_chunk(worker_id: int, rows: list, cfg: CouncilConfig, args) -> None:
    """Enrich a partition of rows in an isolated browser + DB session."""
    prefix = f"[W{worker_id}]"
    total = len(rows)
    conn = get_connection()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not getattr(args, "headed", False))
        context = browser.new_context(
            user_agent=USER_AGENT,
            ignore_https_errors=cfg["ignore_https_errors"],
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            log.info(f"{prefix} Session ready — {total} records to process")
            consecutive_errors = 0

            for i, (app_num, app_type) in enumerate(rows, 1):
                try:
                    log.info(f"{prefix} [{i}/{total}] {app_num}")
                    enrich_one(page, conn, cfg, app_num, app_type)
                    consecutive_errors = 0
                except Exception as e:
                    log.error(f"{prefix}   Error on {app_num}: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        log.error(f"{prefix}   5 consecutive errors — stopping")
                        break
                    try:
                        upsert_detail(conn, cfg, app_num, {})
                    except Exception as upsert_err:
                        log.warning(f"{prefix}   Could not mark {app_num} as failed: {upsert_err}")

            log.info(f"{prefix} Enrichment complete")
        finally:
            browser.close()
            conn.close()


def run_enrich(conn, cfg: CouncilConfig, args) -> None:
    """Fetch unenriched rows then dispatch to N parallel worker sessions."""
    table = cfg["parent_table"]
    cur = conn.cursor()

    target_app = getattr(args, "app", None)
    if target_app:
        cur.execute(
            f"SELECT application_number, application_type FROM {table} "
            f"WHERE application_number = %s",
            (target_app,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            log.error(f"Application '{target_app}' not found in database")
            return
        _enrich_chunk(0, [row], cfg, args)
        return

    conditions = ["detail_scraped_at IS NULL"]
    if not getattr(args, "include_closed", False):
        conditions.append("monitoring_status = 'active'")

    sql = f"""
        SELECT application_number, application_type
        FROM {table}
        WHERE {' AND '.join(conditions)}
        ORDER BY lodgement_date DESC NULLS LAST
    """
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    cur.execute(sql)
    rows = [(r[0], r[1]) for r in cur.fetchall()]
    cur.close()

    workers = max(1, getattr(args, "workers", 2))
    log.info(f"{len(rows)} applications to enrich across {workers} worker(s)")
    if not rows:
        return

    chunks = [rows[i::workers] for i in range(workers)]
    chunks = [c for c in chunks if c]

    if len(chunks) == 1:
        _enrich_chunk(0, chunks[0], cfg, args)
    else:
        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            futures = {
                executor.submit(_enrich_chunk, i, chunk, cfg, args): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Worker {worker_id} raised unhandled exception: {e}")


def run_monitor(conn, cfg: CouncilConfig, args) -> None:
    """Re-check active applications for status/detail changes."""
    table = cfg["parent_table"]
    cur = conn.cursor()
    sql = f"""
        SELECT application_number, application_type
        FROM {table}
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

    # Monitor uses threaded enrichment too
    workers = max(1, getattr(args, "workers", 1))
    chunks = [rows[i::workers] for i in range(workers)]
    chunks = [c for c in chunks if c]

    if len(chunks) == 1:
        _enrich_chunk(0, chunks[0], cfg, args)
    else:
        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            futures = {
                executor.submit(_enrich_chunk, i, chunk, cfg, args): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Worker {worker_id} raised unhandled exception: {e}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser(council_name: str, groups: dict) -> argparse.ArgumentParser:
    """Build the argparse parser for a council import script."""
    parser = argparse.ArgumentParser(
        description=f"Import {council_name} development applications from Development.i"
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true",
                      help="Full import from start date to now")
    mode.add_argument("--enrich", action="store_true",
                      help="Enrich existing records with detail-page data")
    mode.add_argument("--monitor", action="store_true",
                      help="Re-check active applications for updates")
    parser.add_argument("--days", type=int, default=30,
                        help="Delta: scrape last N days (default 30)")
    parser.add_argument("--from-date", type=str,
                        help="Start date YYYY-MM-DD (overrides --days)")
    parser.add_argument("--to-date", type=str,
                        help="End date YYYY-MM-DD")
    parser.add_argument("--group", type=str, choices=list(groups.keys()),
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
    parser.add_argument("--workers", type=int, default=2,
                        help="Parallel browser sessions for --enrich/--monitor (default 2)")

    return parser


def run(cfg: CouncilConfig) -> None:
    """Entry point called by per-council wrapper scripts."""
    parser = build_parser(cfg["name"], cfg["groups"])
    args = parser.parse_args()

    global DELAY
    DELAY = args.delay

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    )
    # Set our logger name to match the council
    global log
    log = logging.getLogger(f"import_{cfg['slug']}_da")

    conn = get_connection()
    log.info(f"Connected to database — council: {cfg['name']}")

    try:
        if args.enrich or args.app:
            run_enrich(conn, cfg, args)
        elif args.monitor:
            run_monitor(conn, cfg, args)
        else:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not args.headed)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    ignore_https_errors=cfg["ignore_https_errors"],
                )
                page = context.new_page()
                page.set_default_timeout(30000)
                try:
                    run_scrape(page, conn, cfg, args)
                finally:
                    browser.close()
    finally:
        conn.close()
