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


# ── Address parsing ──────────────────────────────────────────────────────────

_STREET_TYPES = {
    "ALLEY", "APPROACH", "ARCADE", "AVENUE", "BOULEVARD", "BRACE",
    "BYPASS", "CAUSEWAY", "CIRCUIT", "CIRCUS", "CLOSE", "CONCOURSE",
    "CORNER", "COURT", "COVE", "CRESCENT", "CREST", "DRIVE",
    "ESPLANADE", "FAIRWAY", "FREEWAY", "FRONTAGE", "GLADE", "GLEN",
    "GROVE", "GULLY", "HEIGHTS", "HIGHWAY", "ISLAND", "JUNCTION",
    "LANE", "LINK", "LOOP", "MEWS", "MOTORWAY", "NOOK", "OUTLOOK",
    "PARADE", "PARKWAY", "PASS", "PATHWAY", "PLACE", "PLAZA",
    "PROMENADE", "RAMBLE", "RETREAT", "RIDGE", "RISE", "ROAD",
    "ROUTE", "ROW", "RUN", "SQUARE", "STREET", "STRIP", "TERRACE",
    "TRACK", "TRAIL", "VALE", "VIEW", "VISTA", "WALK", "WAY", "WHARF",
}

# Unit prefix: "UNIT 4, " / "SHOP 3A, " / "FLAT 2, "
_RE_UNIT_PREFIX = re.compile(
    r"^(UNIT|SHOP|FLAT|SUITE|VILLA|APT|APARTMENT)\s+(\d+\w*)\s*,\s*",
    re.IGNORECASE,
)

# Leading lot qualifiers seen in ePathway: BAL, PT1, PT2, P01 etc.
_RE_LOT_QUALIFIER = re.compile(r"^(?:BAL|PT\d+|P\d+)\s+", re.IGNORECASE)

# Lot + plan code (e.g. "Lot 255 WD5121, "): 1–5 letters followed by digits covers all 400+
# QLD plan type prefixes (SP, RP, BUP, GTP, WD, MPH, …) without an explicit list.
_RE_LOT_PLAN = re.compile(r"\bLot\s+\d{1,5}\s+[A-Z]{1,5}\d+,?\s*", re.IGNORECASE)

# Bare "Lot N" remaining after plan code has been stripped
_RE_BARE_LOT = re.compile(r"^Lot\s+\d+\s*", re.IGNORECASE)


def _prepare_address(raw: str) -> str:
    """Strip cadastral lot references from an ePathway address string.

    Leaves a clean street address ready for parsing. Applied in order:
      1. Strip leading qualifier tokens: BAL, PT1, PT2, P01 etc.
      2. Strip all "Lot N PLAN_CODE" pairs (covers all QLD plan types via [A-Z]{1,5}\\d+).
      3. Strip leading comma/whitespace left by step 2.
      4. Strip any remaining bare "Lot N" prefix — the number is NOT preserved as a
         street number (e.g. "Lot 47 Shipper Drive" → "Shipper Drive", unparseable).
    """
    text = _RE_LOT_QUALIFIER.sub("", raw).strip()
    text = _RE_LOT_PLAN.sub("", text)
    text = text.lstrip(", ").strip()
    text = _RE_BARE_LOT.sub("", text).strip()
    return text


def _libpostal_parse(text: str) -> list[dict]:
    """Call the pelias/libpostal-service REST API.

    Returns a list of {"label": ..., "value": ...} dicts, identical in
    structure to what the Python bindings return as (value, label) tuples.
    Raises requests.HTTPError or requests.ConnectionError if the service
    is unavailable.
    """
    import os
    import requests as _requests
    url = os.getenv("LIBPOSTAL_URL", "http://localhost:4400")
    resp = _requests.get(f"{url}/parse", params={"address": text}, timeout=5)
    resp.raise_for_status()
    return resp.json()


def _split_road(road: str) -> tuple[str | None, str | None]:
    """Split libpostal's combined 'road' field into (street_name, street_type).

    Finds the last word that matches a known street type; everything before it
    becomes the street name. Falls back to treating the last word as the type.
    """
    words = road.split()
    type_idx = next(
        (i for i in range(len(words) - 1, -1, -1) if words[i].upper() in _STREET_TYPES),
        None,
    )
    if type_idx is not None:
        street_type = words[type_idx].title()
        street_name = " ".join(w.title() for w in words[:type_idx]) if type_idx > 0 else None
    else:
        street_type = words[-1].title() if words else None
        street_name = " ".join(w.title() for w in words[:-1]) if len(words) > 1 else None
    return street_name, street_type


def parse_location_address(addr: str | None) -> ParsedAddress:
    """Parse a free-text ePathway location address into structured fields.

    Strips cadastral lot references first (_prepare_address), then delegates
    to the pelias/libpostal-service REST API for parsing. The service must be
    running (see docker-compose.yml at project root).

    Handles formats seen in ePathway summary and property section rows:
      "2 River Terrace"
      "UNIT 4, 19 Santa Barbara Road"
      "Lot 255 WD5121, 55 Eden Avenue, COOLANGATTA QLD 4225"
      "BAL Lot 1 RP215138, 82 Cabbage Tree Point Road"
      "Lot 303 SP289809"              ← bare lot ref, returns all-None
    """
    out: ParsedAddress = {
        "unit_type": None, "unit_number": None, "unit_suffix": None,
        "street_number": None, "street_name": None, "street_type": None,
        "suburb": None, "postcode": None,
    }
    if not addr:
        return out

    text = _prepare_address(addr.strip())
    if not text:
        return out  # bare lot ref, nothing parseable

    # Extract unit_type before libpostal — libpostal drops type keywords (UNIT/SHOP/FLAT)
    m = _RE_UNIT_PREFIX.match(text)
    if m:
        out["unit_type"] = m.group(1).upper()

    for component in _libpostal_parse(text):
        label = component["label"]
        value = component["value"].strip()
        if label == "house_number":
            out["street_number"] = value
        elif label == "unit":
            # libpostal includes the type keyword in the value (e.g. "unit 4") — strip it
            out["unit_number"] = re.sub(
                r"^(UNIT|SHOP|FLAT|SUITE|VILLA|APT|APARTMENT)\s+",
                "",
                value,
                flags=re.IGNORECASE,
            )
        elif label == "road":
            out["street_name"], out["street_type"] = _split_road(value)
        elif label in ("city", "suburb"):
            # libpostal labels Australian suburbs as either "suburb" or "city" depending
            # on how well-known the locality is — treat both the same
            out["suburb"] = value.title()
        elif label == "postcode":
            out["postcode"] = value

    return out
