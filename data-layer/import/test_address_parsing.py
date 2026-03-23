"""
test_address_parsing.py

Parses location_address fields from unmatched DAs and attempts to resolve
each to a current cadastre parcel via qld_cadastre_address.

Outputs a CSV report: original address, parsed components, matched lotplan + address.

Usage:
    python test_address_parsing.py
    python test_address_parsing.py --limit 500
    python test_address_parsing.py --output /tmp/parse_report.csv
"""

import re
import csv
import sys
import os
import argparse
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://realestate:realestate@localhost:5432/realestatev2")

# ── Address format patterns ───────────────────────────────────────────────────

# Format A: "Lot X PLAN, 123 Street Name, SUBURB  QLD  POSTCODE"
# Also handles "Lot X PLAN, 123A Street Name, ..."
RE_FORMAT_A = re.compile(
    r"Lot\s+\d+\s+[A-Z0-9]+,\s*"          # Lot X PLAN,
    r"(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)"   # group 1: street number (67, 67A, 12-14)
    r"\s+(.+?)"                             # group 2: street name + type
    r",\s*([A-Z][A-Z ]+?)\s+"              # group 3: suburb
    r"(QLD)\s+(\d{4})",                    # group 4: state, group 5: postcode
    re.IGNORECASE,
)

# Format C: "Lot X PLAN, UNIT N, 123 Street Name, SUBURB  QLD  POSTCODE"
RE_FORMAT_C = re.compile(
    r"Lot\s+\d+\s+[A-Z0-9]+,\s*"
    r"(?:UNIT|Unit)\s+(\d+),\s*"           # group 1: unit number
    r"(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)"   # group 2: street number
    r"\s+(.+?)"                             # group 3: street name + type
    r",\s*([A-Z][A-Z ]+?)\s+"              # group 4: suburb
    r"(QLD)\s+(\d{4})",                    # group 5: state, group 6: postcode
    re.IGNORECASE,
)

# Format C2: "Lot X PLAN, Unit N, 123 Street" (unit inline, no comma before number)
RE_FORMAT_C2 = re.compile(
    r"Lot\s+\d+\s+[A-Z0-9]+,\s*"
    r"Unit\s+(\d+),\s*"
    r"(\d+[A-Za-z]?)\s+(.+?)"
    r",\s*([A-Z][A-Z ]+?)\s+(QLD)\s+(\d{4})",
    re.IGNORECASE,
)

# Format E: starts directly with a street number (rare)
RE_FORMAT_E = re.compile(
    r"^(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)"
    r"\s+(.+?)"
    r",\s*([A-Z][A-Z ]+?)\s+(QLD)\s+(\d{4})",
    re.IGNORECASE,
)

# Format G (BAL/PT prefix): strip prefix then try Format A
RE_BAL_PT = re.compile(r"^(?:BAL\s+|PT\d+\s+)", re.IGNORECASE)


def classify_format(addr: str) -> str:
    if not addr:
        return "F_no_address"
    a = addr.strip()
    if RE_BAL_PT.match(a):
        return "G_bal_pt"
    if re.match(r"^Lot\s+\d+\s+[A-Z0-9]+\s*$", a, re.IGNORECASE):
        return "F_lot_plan_only"
    if re.match(r"^Lot\s+\d+\s+[A-Z0-9]+,\s*(?:UNIT|Unit)\s+\d+,\s*\d+", a):
        return "C_unit_then_number"
    if re.match(r"^Lot\s+\d+\s+[A-Z0-9]+,\s*(?:UNIT|Unit)\s+\d+,", a):
        return "C_unit_only"
    if re.match(r"^Lot\s+\d+\s+[A-Z0-9]+,\s*Lot\s+\d+\s+[A-Za-z]", a):
        return "B_lot_street_name"
    if re.match(r"^Lot\s+\d+\s+[A-Z0-9]+,\s*\d+", a):
        return "A_standard"
    if re.match(r"^\d+", a):
        return "E_number_first"
    return "G_other"


def split_street_name_type(street_full: str):
    """
    Split 'Twenty Fourth Avenue' into name='Twenty Fourth', type='Avenue'.
    The cadastre stores street_name and street_type separately.
    street_type is always the LAST word.
    """
    parts = street_full.strip().split()
    if len(parts) == 1:
        return street_full.strip(), ""
    return " ".join(parts[:-1]), parts[-1]


def parse_address(addr: str) -> dict | None:
    """
    Returns dict with keys: street_number, street_name, street_type, suburb,
    state, postcode, unit_number — or None if unparseable.
    """
    if not addr:
        return None

    a = addr.strip()

    # Strip BAL/PT prefix and retry as Format A
    bal_match = RE_BAL_PT.match(a)
    if bal_match:
        a = a[bal_match.end():]

    # Format C: unit + street number
    m = RE_FORMAT_C.match(a)
    if m:
        street_name, street_type = split_street_name_type(m.group(3))
        return {
            "unit_number": m.group(1),
            "street_number": m.group(2).upper(),
            "street_name": street_name.upper(),
            "street_type": street_type.upper(),
            "suburb": m.group(4).strip().upper(),
            "state": m.group(5).upper(),
            "postcode": m.group(6),
        }

    # Format A: standard
    m = RE_FORMAT_A.match(a)
    if m:
        street_name, street_type = split_street_name_type(m.group(2))
        return {
            "unit_number": None,
            "street_number": m.group(1).upper(),
            "street_name": street_name.upper(),
            "street_type": street_type.upper(),
            "suburb": m.group(3).strip().upper(),
            "state": m.group(4).upper(),
            "postcode": m.group(5),
        }

    # Format E: starts with street number
    m = RE_FORMAT_E.match(a)
    if m:
        street_name, street_type = split_street_name_type(m.group(2))
        return {
            "unit_number": None,
            "street_number": m.group(1).upper(),
            "street_name": street_name.upper(),
            "street_type": street_type.upper(),
            "suburb": m.group(3).strip().upper(),
            "state": m.group(4).upper(),
            "postcode": m.group(5),
        }

    return None


def lookup_cadastre(cur, parsed: dict) -> list[dict]:
    """
    Query qld_cadastre_address for matching parcels.
    Returns list of {lotplan, address, plan} dicts.
    """
    # Try with street_type first (most precise)
    sql = """
        SELECT lotplan, address, plan, lot
        FROM qld_cadastre_address
        WHERE street_number = %(street_number)s
          AND UPPER(street_name) = %(street_name)s
          AND UPPER(street_type) = %(street_type)s
          AND UPPER(locality) = %(suburb)s
        LIMIT 10
    """
    cur.execute(sql, parsed)
    rows = cur.fetchall()
    if rows:
        return [dict(r) for r in rows]

    # Fallback: without street_type (handles 'Terrace N' → 'Terrace' mismatches)
    sql_no_type = """
        SELECT lotplan, address, plan, lot
        FROM qld_cadastre_address
        WHERE street_number = %(street_number)s
          AND UPPER(street_name) = %(street_name)s
          AND UPPER(locality) = %(suburb)s
        LIMIT 10
    """
    cur.execute(sql_no_type, parsed)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit rows processed (0 = all)")
    parser.add_argument("--output", default="address_parse_report.csv")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Fetch all unmatched DA property rows (cadastre_lotplan unresolved) with a location_address
    limit_clause = f"LIMIT {args.limit}" if args.limit else ""
    cur.execute(f"""
        SELECT da.application_number, dp.lot_on_plan AS lot_plan, dp.location_address,
               da.application_type, da.development_category
        FROM goldcoast_da_properties dp
        JOIN goldcoast_dev_applications da ON da.application_number = dp.application_number
        WHERE dp.cadastre_lotplan IS NULL
          AND dp.location_address IS NOT NULL
        ORDER BY da.application_number
        {limit_clause}
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    das = [dict(zip(cols, r)) for r in rows]

    print(f"Processing {len(das)} unmatched DAs with location_address...", file=sys.stderr)

    # Stats
    stats = {
        "total": len(das),
        "format_counts": {},
        "parsed": 0,
        "matched_exact": 0,
        "matched_fallback": 0,
        "no_match": 0,
        "unparseable": 0,
    }

    lookup_cur = conn.cursor()
    lookup_cur.row_factory = None

    report_rows = []

    for da in das:
        addr = da["location_address"]
        fmt = classify_format(addr)
        stats["format_counts"][fmt] = stats["format_counts"].get(fmt, 0) + 1

        parsed = parse_address(addr)

        if not parsed:
            stats["unparseable"] += 1
            report_rows.append({
                "application_number": da["application_number"],
                "lot_plan": da["lot_plan"],
                "original_address": addr,
                "format": fmt,
                "parsed_street_number": "",
                "parsed_street_name": "",
                "parsed_street_type": "",
                "parsed_suburb": "",
                "parsed_state": "",
                "parsed_postcode": "",
                "match_count": 0,
                "matched_lotplans": "",
                "matched_addresses": "",
                "match_type": "UNPARSEABLE",
            })
            continue

        stats["parsed"] += 1

        # Lookup in cadastre
        lookup_cur.execute("""
            SELECT lotplan, address, plan, lot
            FROM qld_cadastre_address
            WHERE street_number = %s
              AND UPPER(street_name) = %s
              AND UPPER(street_type) = %s
              AND UPPER(locality) = %s
            LIMIT 10
        """, (parsed["street_number"], parsed["street_name"], parsed["street_type"], parsed["suburb"]))
        matches = lookup_cur.fetchall()
        match_type = "EXACT" if matches else None

        if not matches:
            # Fallback without street_type
            lookup_cur.execute("""
                SELECT lotplan, address, plan, lot
                FROM qld_cadastre_address
                WHERE street_number = %s
                  AND UPPER(street_name) = %s
                  AND UPPER(locality) = %s
                LIMIT 10
            """, (parsed["street_number"], parsed["street_name"], parsed["suburb"]))
            matches = lookup_cur.fetchall()
            match_type = "FALLBACK_NO_TYPE" if matches else None

        if matches:
            if match_type == "EXACT":
                stats["matched_exact"] += 1
            else:
                stats["matched_fallback"] += 1
        else:
            stats["no_match"] += 1
            match_type = "NO_MATCH"

        report_rows.append({
            "application_number": da["application_number"],
            "lot_plan": da["lot_plan"],
            "original_address": addr,
            "format": fmt,
            "parsed_street_number": parsed.get("street_number", ""),
            "parsed_street_name": parsed.get("street_name", ""),
            "parsed_street_type": parsed.get("street_type", ""),
            "parsed_suburb": parsed.get("suburb", ""),
            "parsed_state": parsed.get("state", ""),
            "parsed_postcode": parsed.get("postcode", ""),
            "match_count": len(matches),
            "matched_lotplans": " | ".join(m[0] for m in matches),
            "matched_addresses": " | ".join(m[1] for m in matches),
            "match_type": match_type,
        })

    # Write CSV
    fieldnames = [
        "application_number", "lot_plan", "original_address", "format",
        "parsed_street_number", "parsed_street_name", "parsed_street_type",
        "parsed_suburb", "parsed_state", "parsed_postcode",
        "match_count", "matched_lotplans", "matched_addresses", "match_type",
    ]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    # Print summary
    print(f"\n{'='*60}")
    print(f"PARSING REPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total unmatched DAs with address : {stats['total']}")
    print(f"")
    print(f"FORMAT BREAKDOWN:")
    for fmt, count in sorted(stats["format_counts"].items(), key=lambda x: -x[1]):
        print(f"  {fmt:<30} {count:>6}")
    print(f"")
    print(f"PARSE RESULTS:")
    print(f"  Parsed successfully            : {stats['parsed']}")
    print(f"  Unparseable                    : {stats['unparseable']}")
    print(f"")
    print(f"CADASTRE MATCH RESULTS (of parsed):")
    print(f"  Exact match (with street type) : {stats['matched_exact']}")
    print(f"  Fallback match (no street type): {stats['matched_fallback']}")
    print(f"  No match found                 : {stats['no_match']}")
    total_matched = stats["matched_exact"] + stats["matched_fallback"]
    pct = round(total_matched / stats["total"] * 100, 1) if stats["total"] else 0
    print(f"")
    print(f"  TOTAL RESOLVED via address     : {total_matched} / {stats['total']} ({pct}%)")
    print(f"{'='*60}")
    print(f"\nReport written to: {args.output}", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main()
