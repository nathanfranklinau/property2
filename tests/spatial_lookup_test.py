"""
Spatial cadastre lookup accuracy test using Google Address Validation API.

Samples 50 random QLD addresses from GNAF (mix of property types), geocodes
each with Google's Address Validation API, then tests whether a spatial
ST_Contains lookup against qld_cadastre_parcels finds the correct parcel.

Usage:
    cd realestatev2
    source data-layer/venv/bin/activate
    GOOGLE_MAPS_API_KEY=<key> python tests/spatial_lookup_test.py
    # or export GOOGLE_MAPS_API_KEY first

Output:
    tests/spatial_lookup_test_results.csv
"""

import csv
import os
import sys
import time
import requests
import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://realestate:realestate@localhost:5432/realestatev2",
)
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "spatial_lookup_test_results.csv")

SAMPLES_PER_CATEGORY = {
    "single_dwelling": 15,
    "unit":            10,
    "townhouse":        5,
    "apartment":        5,
    "flat":             5,
    "duplex":           3,
    "villa":            3,
    "house":            2,
    "shop":             2,
}


def get_sample_addresses(conn):
    addresses = []
    for category, count in SAMPLES_PER_CATEGORY.items():
        if category == "single_dwelling":
            flat_filter = "AND ad.flat_type_code IS NULL"
        else:
            code_map = {
                "unit": "UNIT", "townhouse": "TNHS", "apartment": "APT",
                "flat": "FLAT", "duplex": "DUPL", "villa": "VLLA",
                "house": "HSE", "shop": "SHOP",
            }
            flat_filter = f"AND ad.flat_type_code = '{code_map[category]}'"

        query = f"""
            SELECT
                ad.number_first,
                ad.number_first_suffix,
                ad.flat_type_code,
                ad.flat_number,
                sl.street_name,
                sl.street_type_code,
                l.locality_name,
                ad.postcode,
                ad.legal_parcel_id
            FROM gnaf_data_address_detail ad
            JOIN gnaf_data_street_locality sl ON sl.street_locality_pid = ad.street_locality_pid
            JOIN gnaf_data_locality l ON l.locality_pid = ad.locality_pid
            JOIN gnaf_data_state s ON s.state_pid = l.state_pid
            WHERE s.state_abbreviation = 'QLD'
              AND ad.date_retired IS NULL
              AND ad.legal_parcel_id IS NOT NULL AND ad.legal_parcel_id <> ''
              AND POSITION('/' IN ad.legal_parcel_id) > 0
              AND ad.number_first IS NOT NULL
              AND sl.street_type_code IS NOT NULL
              {flat_filter}
            ORDER BY RANDOM()
            LIMIT {count}
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                row["category"] = category
                addresses.append(row)
    return addresses


def build_display_address(row):
    parts = []
    if row["flat_type_code"] and row["flat_number"]:
        parts.append(f"{row['flat_type_code']} {int(row['flat_number'])}/")
    num = str(int(row["number_first"]))
    if row.get("number_first_suffix"):
        num += row["number_first_suffix"]
    parts.append(num)
    parts.append(f"{row['street_name']} {row['street_type_code']}")
    parts.append(row["locality_name"])
    parts.append(f"QLD {row['postcode']}")
    return " ".join(parts)


def google_validate(address):
    """
    Call Google Address Validation API, return (lat, lon, formatted_address, verdict).
    Returns (None, None, None, error_msg) on failure.
    """
    url = "https://addressvalidation.googleapis.com/v1:validateAddress"
    payload = {
        "address": {"addressLines": [address]},
        "enableUspsCass": False,
    }
    try:
        resp = requests.post(f"{url}?key={GOOGLE_API_KEY}", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return None, None, None, str(e)

    result = data.get("result", {})
    geocode = result.get("geocode", {})
    location = geocode.get("location", {})
    lat = location.get("latitude")
    lon = location.get("longitude")
    verdict = result.get("verdict", {})
    action = verdict.get("validationGranularity", "unknown")
    formatted = result.get("address", {}).get("formattedAddress", address)

    if lat is None or lon is None:
        return None, None, formatted, "no_geocode"

    return lat, lon, formatted, action


def spatial_lookup(conn, lat, lon):
    """Find the cadastre parcel containing the given point."""
    query = """
        SELECT lot, plan, lot_area,
               ST_Y(ST_Centroid(geometry)) AS centroid_lat,
               ST_X(ST_Centroid(geometry)) AS centroid_lon
        FROM qld_cadastre_parcels
        WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 7844))
          AND parcel_typ = 'Lot Type Parcel'
        ORDER BY lot_area ASC
        LIMIT 1
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, [lon, lat])
        row = cur.fetchone()
    if not row:
        return None, None, None
    return row["lot"], row["plan"], row["lot_area"]


def main():
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DB_URL)

    print("Sampling 50 addresses from GNAF...")
    addresses = get_sample_addresses(conn)
    print(f"Got {len(addresses)} addresses\n")

    results = []
    for i, row in enumerate(addresses, 1):
        display = build_display_address(row)
        gnaf_known = row["legal_parcel_id"]
        gnaf_plan = gnaf_known.split("/")[1] if "/" in gnaf_known else ""
        gnaf_lot  = gnaf_known.split("/")[0] if "/" in gnaf_known else ""

        # Google geocode
        lat, lon, formatted, google_verdict = google_validate(display)
        time.sleep(0.1)  # stay within rate limits

        if lat is None:
            status = "GOOGLE_FAIL"
            spatial_lotplan = None
            spatial_area = None
            correct_plan = False
        else:
            spatial_lot, spatial_plan, spatial_area = spatial_lookup(conn, lat, lon)
            spatial_lotplan = f"{spatial_lot}/{spatial_plan}" if spatial_lot else None

            correct_plan = spatial_plan == gnaf_plan if spatial_plan else False
            status = "PASS" if correct_plan else ("SPATIAL_MISS" if not spatial_plan else "WRONG_PLAN")

        results.append({
            "index":             i,
            "category":          row["category"],
            "input_address":     display,
            "google_formatted":  formatted,
            "google_verdict":    google_verdict,
            "google_lat":        lat,
            "google_lon":        lon,
            "gnaf_known_lotplan": gnaf_known,
            "gnaf_known_plan":   gnaf_plan,
            "spatial_lotplan":   spatial_lotplan,
            "spatial_area_sqm":  spatial_area,
            "correct_plan":      correct_plan,
            "status":            status,
        })

        print(f"  [{i:2d}/50] {status:12s} {display[:55]}")

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # Summary
    total = len(results)
    passed   = sum(1 for r in results if r["status"] == "PASS")
    wrong    = sum(1 for r in results if r["status"] == "WRONG_PLAN")
    miss     = sum(1 for r in results if r["status"] == "SPATIAL_MISS")
    gfail    = sum(1 for r in results if r["status"] == "GOOGLE_FAIL")

    print(f"\n{'='*60}")
    print(f"RESULTS ({total} addresses)")
    print(f"{'='*60}")
    print(f"  PASS  (correct plan):     {passed:3d}/{total}  ({passed/total*100:.0f}%)")
    print(f"  WRONG_PLAN:               {wrong:3d}/{total}")
    print(f"  SPATIAL_MISS (no result): {miss:3d}/{total}")
    print(f"  GOOGLE_FAIL:              {gfail:3d}/{total}")

    print(f"\nBy category:")
    cats = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r["status"] == "PASS")
    for cat, outcomes in cats.items():
        pct = sum(outcomes) / len(outcomes) * 100
        print(f"  {cat:15}: {sum(outcomes)}/{len(outcomes)} ({pct:.0f}%)")

    print(f"\nReport: {OUTPUT_CSV}")
    conn.close()


if __name__ == "__main__":
    main()
