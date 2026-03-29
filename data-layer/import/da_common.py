"""Shared utilities for QLD development application import scripts.

Used by both import_goldcoast_da.py and import_brisbane_da.py.
"""

import os
import re
from datetime import date, datetime, timedelta
from typing import TypedDict

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

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


class ParsedAddress(TypedDict):
    unit_type: str | None
    unit_number: str | None
    unit_suffix: str | None
    street_number: str | None
    street_name: str | None
    street_type: str | None
    suburb: str | None
    postcode: str | None


class ParsedDescription(TypedDict):
    development_category: str | None
    dwelling_type: str | None
    unit_count: int | None
    lot_split_from: int | None
    lot_split_to: int | None
    assessment_level: str | None


def is_terminal(status: str | None) -> bool:
    """Return True if this status means the application lifecycle is over."""
    if not status:
        return False
    return status.strip().lower() in TERMINAL_STATUSES


def monitoring_status_for(status: str | None) -> str:
    return "closed" if is_terminal(status) else "active"


# ── DB connection ─────────────────────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


# ── Date helpers ──────────────────────────────────────────────────────────────

def parse_au_date(s: str) -> date | None:
    """Parse DD/MM/YYYY → date, or return None."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def month_ranges(start: date, end: date) -> list[tuple[date, date]]:
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


def parse_description(description: str | None, application_type: str | None) -> ParsedDescription:
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


# ── Cadastre resolution ──────────────────────────────────────────────────────

# Matches bare lot/plan references in a location_address field, e.g.:
#   "Lot 9 SP180076"  → lot="9",  plan="SP180076"
#   "Lot 9A SP180076" → lot="9A", plan="SP180076"
#   "9 SP180076"      → lot="9",  plan="SP180076"
# Does NOT match street addresses ("41 Smith Street MIAMI") because the plan
# segment requires 2+ uppercase letters followed by 4+ digits.
_LOT_PLAN_RE = re.compile(
    r"(?i)^\s*(?:Lot\s+)?(\w+)\s+([A-Z]{2,}\d{4,})\b"
)


def extract_lot_plan_from_location_address(address: str | None) -> str | None:
    """Extract a normalised lot+plan string from a location_address field.

    Returns e.g. "9SP180076" when address is "Lot 9 SP180076", or None when
    the address is a street address or cannot be parsed as a lot reference.
    """
    if not address:
        return None
    m = _LOT_PLAN_RE.match(address.strip())
    if not m:
        return None
    return m.group(1) + m.group(2).upper()


def resolve_cadastre_lotplan(conn: psycopg2.extensions.connection, lot_plan: str) -> str | None:
    """Resolve a DA lot_plan to the matching lotplan in qld_cadastre_parcels.

    Strategy:
      1. Exact match in qld_cadastre_parcels → return that lotplan
      2. Match in qld_cadastre_address (unit lot not in parcels) → return the
         largest Lot Type Parcel for that plan (Lot 0 common property)
      3. No match → None

    Returns a full lot+plan string (e.g. "0SP267345"), suitable for direct
    equality joins against qld_cadastre_parcels.lotplan.
    """
    if not lot_plan:
        return None
    cur = conn.cursor()
    # Step 1: exact match in parcels
    cur.execute(
        "SELECT lotplan FROM qld_cadastre_parcels WHERE lotplan = %s LIMIT 1",
        (lot_plan,),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0]
    # Step 2: unit lot — match via address table, resolve to common property parcel
    cur.execute(
        "SELECT plan FROM qld_cadastre_address WHERE lotplan = %s LIMIT 1",
        (lot_plan,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    plan = row[0]
    cur.execute(
        """
        SELECT lotplan FROM qld_cadastre_parcels
        WHERE plan = %s AND parcel_typ = 'Lot Type Parcel' AND lot_area > 0
        ORDER BY lot_area DESC
        LIMIT 1
        """,
        (plan,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def lookup_suburb_from_cadastre(conn: psycopg2.extensions.connection, lot_plan: str) -> str | None:
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


def lookup_cadastre_suburb(cur: psycopg2.extensions.cursor, cadastre_lp: str) -> str | None:
    """Return the locality for a resolved cadastre lotplan.

    Tries qld_cadastre_address first (has address rows for individual lots),
    falls back to qld_cadastre_parcels (has locality for all parcel types
    including common property Lot 0).
    """
    cur.execute(
        "SELECT locality FROM qld_cadastre_address WHERE lotplan = %s LIMIT 1",
        (cadastre_lp,),
    )
    row = cur.fetchone()
    if row and row[0]:
        return row[0]
    cur.execute(
        "SELECT locality FROM qld_cadastre_parcels WHERE lotplan = %s LIMIT 1",
        (cadastre_lp,),
    )
    row = cur.fetchone()
    return row[0] if row else None



def parse_location_address(addr: str | None) -> ParsedAddress:
    """Parse a free-text location address into structured fields.

    Stub — returns all-None. Will be replaced with the DistilBERT address
    parser once the model is trained. Parsed address columns will be backfilled
    at that point.
    """
    return {
        "unit_type": None, "unit_number": None, "unit_suffix": None,
        "street_number": None, "street_name": None, "street_type": None,
        "suburb": None, "postcode": None,
    }
