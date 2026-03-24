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

# Plan code pattern: 2–4 letters followed by digits (RP4775, SP289809, GTP103559)
_RE_PLAN_CODE = re.compile(r"^[A-Z]{2,4}\d+$", re.IGNORECASE)

# Unit prefix: "UNIT 4, " / "SHOP 3A, " / "FLAT 2, "
_RE_UNIT_PREFIX = re.compile(
    r"^(UNIT|SHOP|FLAT|SUITE|VILLA|APT|APARTMENT)\s+(\d+\w*)\s*,\s*",
    re.IGNORECASE,
)

# Trailing suburb / state / postcode: ", HOPE ISLAND QLD 4212" etc.
_RE_SUBURB_SUFFIX = re.compile(
    r",?\s+[A-Z][A-Z ]+\s+(?:QLD|NSW|VIC|SA|WA|TAS|ACT|NT)\s+\d{4}\s*$"
    r"|,?\s+(?:QLD|NSW|VIC|SA|WA|TAS|ACT|NT)\s+\d{4}\s*$"
    r"|,?\s+\d{4}\s*$",
)

# Capture suburb + postcode from the trailing suffix (named groups)
_RE_SUBURB_CAPTURE = re.compile(
    r",?\s+([A-Z][A-Z ]*?)\s+(?:QLD|NSW|VIC|SA|WA|TAS|ACT|NT)\s+(\d{4})\s*$",
    re.IGNORECASE,
)
_RE_PC_ONLY_CAPTURE = re.compile(r",?\s+(\d{4})\s*$")


def parse_location_address(addr: str | None) -> ParsedAddress:
    """Parse a free-text location address into structured fields.

    Handles formats seen in ePathway / Development.i Property section rows:
      "2 River Terrace"
      "1A Bakers Ridge Drive"
      "2-12 Coomera Grand Drive"
      "UNIT 4, 19 Santa Barbara Road"
      "Lot 47 Shipper Drive"          ← lot number IS the street number
      "Lot 303 SP289809"              ← bare lot ref, nothing parseable

    Returns dict with keys: unit_type, unit_number, unit_suffix,
                            street_number, street_name, street_type.
    All values are str or None.
    """
    out: ParsedAddress = {
        "unit_type": None, "unit_number": None, "unit_suffix": None,
        "street_number": None, "street_name": None, "street_type": None,
        "suburb": None, "postcode": None,
    }
    if not addr:
        return out

    text = addr.strip()

    # --- Extract suburb + postcode from trailing suffix before stripping ---
    m_suburb = _RE_SUBURB_CAPTURE.search(text)
    if m_suburb:
        out["suburb"] = m_suburb.group(1).strip().title()
        out["postcode"] = m_suburb.group(2)
    else:
        m_pc = _RE_PC_ONLY_CAPTURE.search(text)
        if m_pc:
            out["postcode"] = m_pc.group(1)

    # --- Unit prefix ---
    m = _RE_UNIT_PREFIX.match(text)
    if m:
        out["unit_type"] = m.group(1).upper()
        out["unit_number"] = m.group(2)
        text = text[m.end():]

    # --- "Lot N ..." prefix ---
    lot_match = re.match(r"^Lot\s+(\S+)\s+(.*)", text, re.IGNORECASE)
    if lot_match:
        lot_num = lot_match.group(1)
        rest = lot_match.group(2).strip()
        # "Lot NNN PLAN, ACTUAL_ADDRESS" — ePathway summary table prepends the
        # cadastre ref (any letters+digit token) to the street address.
        # Strip it and parse the remainder.
        plan_comma = re.match(r"^([A-Z]+\d\w*),\s*(.*)", rest, re.IGNORECASE)
        if plan_comma and plan_comma.group(2).strip():
            remainder = plan_comma.group(2).strip()
            # Unit prefix may appear after the plan code (e.g. "UNIT 29, 96 Galleon Way")
            unit_m = _RE_UNIT_PREFIX.match(remainder)
            if unit_m:
                out["unit_type"] = unit_m.group(1).upper()
                out["unit_number"] = unit_m.group(2)
                remainder = remainder[unit_m.end():]
            # Remainder may itself start with "Lot NN" where lot = street number
            nested_lot = re.match(r"^Lot\s+(\S+)\s+(.*)", remainder, re.IGNORECASE)
            if nested_lot:
                nested_first = nested_lot.group(2).split()[0] if nested_lot.group(2).strip() else ""
                if re.match(r"^[A-Z]+\d", nested_first, re.IGNORECASE):
                    return out  # nested bare lot ref
                text = f"{nested_lot.group(1)} {nested_lot.group(2)}".strip()
            else:
                text = remainder
        else:
            # No plan+comma — bare lot ref or lot number IS the street number
            first_token = rest.split()[0] if rest else ""
            if _RE_PLAN_CODE.match(first_token):
                return out
            text = f"{lot_num} {rest}"

    # --- Strip trailing suburb / state / postcode ---
    text = _RE_SUBURB_SUFFIX.sub("", text).strip()

    # --- Street number ---
    num_match = re.match(r"^(\d+\w*(?:-\d+\w*)?)\s+(.+)$", text)
    if not num_match:
        return out

    out["street_number"] = num_match.group(1)
    remainder = num_match.group(2).strip()

    # --- Street name + type ---
    words = remainder.split()
    # Find the last word that is a known street type
    type_idx = next(
        (i for i in range(len(words) - 1, -1, -1) if words[i].upper() in _STREET_TYPES),
        None,
    )
    if type_idx is not None:
        out["street_type"] = words[type_idx].title()
        if type_idx > 0:
            out["street_name"] = " ".join(w.title() for w in words[:type_idx])
    else:
        # No recognised type — last word as type, rest as name
        out["street_type"] = words[-1].title() if words else None
        if len(words) > 1:
            out["street_name"] = " ".join(w.title() for w in words[:-1])

    return out


# Brisbane portal uses abbreviated street types (RD, ST, AVE, …) not full words.
_BRISBANE_ABBREVS = {
    "RD": "Road",       "ST": "Street",    "AVE": "Avenue",   "AV": "Avenue",
    "CT": "Court",      "DR": "Drive",     "PL": "Place",     "CL": "Close",
    "CR": "Crescent",   "CRS": "Crescent", "GR": "Grove",     "TCE": "Terrace",
    "HWY": "Highway",   "BLVD": "Boulevard", "PKWY": "Parkway",
    "CSO": "Causeway",  "CCT": "Circuit",  "CIR": "Circuit",
    "ESP": "Esplanade", "MWY": "Motorway", "SQ": "Square",
    "WY": "Way",        "WK": "Walk",      "TR": "Trail",
    "PDE": "Parade",    "PROM": "Promenade", "RDGE": "Ridge",
    "ROW": "Row",       "RISE": "Rise",
}

# Union of abbreviated and full-form types for type-detection
_BRISBANE_ALL_TYPES: dict = {
    **_BRISBANE_ABBREVS,
    **{t: t.title() for t in _STREET_TYPES},
}

_RE_BRISBANE_STATE_PC = re.compile(
    r"\s+(?:QLD|NSW|VIC|SA|WA|TAS|ACT|NT)\s+\d{4}\s*$"
)


def parse_brisbane_address(addr: str | None) -> ParsedAddress:
    """Parse a Brisbane Development.i portal location_address into structured fields.

    Format: 'NUMBER STREET_NAME TYPE  SUBURB  QLD  POSTCODE'
    Street types are abbreviated (RD, ST, AVE, …); no comma before suburb.
    Double spaces separate suburb from QLD/postcode, but single spaces separate
    all other tokens — so we strip state+postcode first, then work backwards
    through the remaining words to find the last known street type.

    Returns dict with keys: unit_type, unit_number, unit_suffix,
                            street_number, street_name, street_type,
                            suburb, postcode.
    """
    out: ParsedAddress = {
        "unit_type": None, "unit_number": None, "unit_suffix": None,
        "street_number": None, "street_name": None, "street_type": None,
        "suburb": None, "postcode": None,
    }
    if not addr:
        return out

    text = addr.strip()

    # Unit prefix: "UNIT 3/89 …" or "3/89 …"
    m = re.match(
        r"^(?:(UNIT|FLAT|APT|SHOP|SUITE)\s+)?(\d+\w*)\s*/\s*(.+)$",
        text, re.IGNORECASE,
    )
    if m:
        out["unit_type"] = (m.group(1) or "UNIT").upper()
        out["unit_number"] = m.group(2)
        text = m.group(3).strip()

    # Extract postcode before stripping state+postcode
    pc_m = re.search(r"\s+(?:QLD|NSW|VIC|SA|WA|TAS|ACT|NT)\s+(\d{4})\s*$", text)
    if pc_m:
        out["postcode"] = pc_m.group(1)

    # Strip state + postcode
    text = _RE_BRISBANE_STATE_PC.sub("", text).strip()

    # Now: "89 DAYS RD GRANGE" / "184 COOPERS CAMP RD ASHGROVE" etc.
    words = text.split()
    if len(words) < 2:
        return out

    # First token must be the street number
    if not re.match(r"^\d+\w*(?:-\d+\w*)?$", words[0]):
        return out
    out["street_number"] = words[0]
    rest = words[1:]  # [name_words… type suburb_words…]

    # Find the LAST word that is a known abbreviated or full street type.
    type_idx = next(
        (i for i in range(len(rest) - 1, -1, -1) if rest[i].upper() in _BRISBANE_ALL_TYPES),
        None,
    )
    if type_idx is None:
        return out

    out["street_type"] = _BRISBANE_ALL_TYPES[rest[type_idx].upper()]
    if type_idx > 0:
        out["street_name"] = " ".join(w.title() for w in rest[:type_idx])

    # Suburb = tokens after the street type
    if type_idx < len(rest) - 1:
        out["suburb"] = " ".join(w.title() for w in rest[type_idx + 1:])

    return out
