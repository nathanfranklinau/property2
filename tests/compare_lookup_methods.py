"""
Compare GNAF text-matching vs spatial cadastre lookup for address → lot/plan resolution.

Picks 50 random QLD addresses from GNAF (mix of property types) and for each:
  1. GNAF method: text-match on street number/name/locality → legal_parcel_id → lot/plan
  2. Spatial method: use GNAF geocode lat/lon → ST_Contains against qld_cadastre_parcels

Outputs a CSV report comparing the two methods.

Usage:
    cd realestatev2
    source data-layer/venv/bin/activate
    python tests/compare_lookup_methods.py
"""

import csv
import os
import sys
import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://realestate:realestate@localhost:5432/realestatev2",
)

OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "lookup_comparison_report.csv")

# How many addresses to sample per category
SAMPLES_PER_CATEGORY = {
    "single_dwelling": 15,  # no flat_type_code, single legal_parcel_id at that number
    "unit": 10,             # flat_type_code = 'UNIT'
    "townhouse": 5,         # flat_type_code = 'TNHS'
    "apartment": 5,         # flat_type_code = 'APT'
    "flat": 5,              # flat_type_code = 'FLAT'
    "duplex": 3,            # flat_type_code = 'DUPL'
    "villa": 3,             # flat_type_code = 'VLLA'
    "house": 2,             # flat_type_code = 'HSE'
    "shop": 2,              # flat_type_code = 'SHOP'
}


def get_sample_addresses(conn):
    """Pull random addresses from GNAF across property type categories."""
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
                ad.address_detail_pid,
                ad.number_first,
                ad.number_first_suffix,
                sl.street_name,
                sl.street_type_code,
                l.locality_name,
                ad.postcode,
                s.state_abbreviation,
                ad.flat_type_code,
                ad.flat_number,
                ad.legal_parcel_id,
                g.latitude,
                g.longitude
            FROM gnaf_data_address_detail ad
            JOIN gnaf_data_street_locality sl ON sl.street_locality_pid = ad.street_locality_pid
            JOIN gnaf_data_locality l ON l.locality_pid = ad.locality_pid
            JOIN gnaf_data_state s ON s.state_pid = l.state_pid
            JOIN gnaf_data_address_default_geocode g
              ON g.address_detail_pid = ad.address_detail_pid AND g.date_retired IS NULL
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
            rows = cur.fetchall()
            for row in rows:
                row["category"] = category
                addresses.append(row)

    return addresses


def build_display_address(row):
    """Reconstruct a human-readable address from GNAF components."""
    parts = []
    if row["flat_type_code"] and row["flat_number"]:
        parts.append(f"{row['flat_type_code']} {row['flat_number']}/")
    num = str(row["number_first"])
    if row.get("number_first_suffix"):
        num += row["number_first_suffix"]
    parts.append(num)
    parts.append(f"{row['street_name']} {row['street_type_code']}")
    parts.append(row["locality_name"])
    parts.append(f"QLD {row['postcode']}")
    return " ".join(parts)


def gnaf_lookup(conn, row):
    """
    Simulate the GNAF text-matching method.
    Match on number_first + street_name + street_type_code + locality + postcode.
    Group by plan, pick the plan with most addresses.
    """
    query = """
        SELECT
            SUBSTRING(ad.legal_parcel_id FROM POSITION('/' IN ad.legal_parcel_id) + 1) AS plan,
            COUNT(DISTINCT ad.legal_parcel_id)::text AS lot_count,
            MIN(ad.legal_parcel_id) AS sample_lot
        FROM gnaf_data_address_detail ad
        JOIN gnaf_data_street_locality sl ON sl.street_locality_pid = ad.street_locality_pid
        JOIN gnaf_data_locality l ON l.locality_pid = ad.locality_pid
        JOIN gnaf_data_state s ON s.state_pid = l.state_pid
        WHERE ad.number_first = %s
          AND UPPER(sl.street_name || ' ' || COALESCE(sl.street_type_code, '')) = UPPER(%s)
          AND UPPER(l.locality_name) = UPPER(%s)
          AND ad.postcode = %s
          AND s.state_abbreviation = 'QLD'
          AND ad.date_retired IS NULL
          AND ad.legal_parcel_id IS NOT NULL AND ad.legal_parcel_id <> ''
          AND POSITION('/' IN ad.legal_parcel_id) > 0
        GROUP BY plan
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    street_full = f"{row['street_name']} {row['street_type_code']}"
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, [row["number_first"], street_full, row["locality_name"], row["postcode"]])
        result = cur.fetchone()

    if not result:
        return None, None, None, 0

    plan = result["plan"]
    lot_count = int(result["lot_count"])
    if lot_count == 1:
        sample = result["sample_lot"]
        lot = sample.split("/")[0] if "/" in sample else None
    else:
        lot = "COMPLEX"

    return lot, plan, lot_count, lot_count


def spatial_lookup(conn, lat, lon):
    """
    Spatial method: find the cadastre parcel that contains the geocode point.
    """
    query = """
        SELECT lot, plan, lot_area,
               ST_Y(ST_Centroid(geometry)) AS centroid_lat,
               ST_X(ST_Centroid(geometry)) AS centroid_lon
        FROM qld_cadastre_parcels
        WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 7844))
          AND parcel_typ = 'Lot Type Parcel'
        ORDER BY lot_area DESC
        LIMIT 1
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, [lon, lat])
        result = cur.fetchone()

    if not result:
        return None, None, None

    return result["lot"], result["plan"], result["lot_area"]


def main():
    conn = psycopg2.connect(DB_URL)

    print("Sampling 50 addresses from GNAF...")
    addresses = get_sample_addresses(conn)
    print(f"Got {len(addresses)} addresses\n")

    results = []
    for i, row in enumerate(addresses, 1):
        display = build_display_address(row)
        gnaf_legal = row["legal_parcel_id"]
        gnaf_lot_raw = gnaf_legal.split("/")[0] if "/" in gnaf_legal else ""
        gnaf_plan_raw = gnaf_legal.split("/")[1] if "/" in gnaf_legal else ""

        # Method 1: GNAF text matching
        gnaf_lot, gnaf_plan, gnaf_lot_count, _ = gnaf_lookup(conn, row)

        # Method 2: Spatial lookup using geocode
        spatial_lot, spatial_plan, spatial_area = spatial_lookup(
            conn, row["latitude"], row["longitude"]
        )

        # Compare
        gnaf_lotplan = f"{gnaf_lot}/{gnaf_plan}" if gnaf_lot and gnaf_plan else None
        spatial_lotplan = f"{spatial_lot}/{spatial_plan}" if spatial_lot and spatial_plan else None

        # Does GNAF method find the correct plan?
        gnaf_plan_match = gnaf_plan == gnaf_plan_raw if gnaf_plan else False
        # Does spatial method find the same plan as GNAF's known answer?
        spatial_plan_match = spatial_plan == gnaf_plan_raw if spatial_plan else False

        # Do both methods agree with each other?
        methods_agree = gnaf_lotplan == spatial_lotplan

        # Is the spatial result a parent lot (different plan, but contains the point)?
        spatial_is_parent = (
            spatial_plan is not None
            and spatial_plan != gnaf_plan_raw
        )

        results.append({
            "index": i,
            "category": row["category"],
            "address": display,
            "gnaf_geocode_lat": row["latitude"],
            "gnaf_geocode_lon": row["longitude"],
            "gnaf_known_lotplan": gnaf_legal,
            "gnaf_method_lotplan": gnaf_lotplan,
            "gnaf_method_lot_count": gnaf_lot_count,
            "gnaf_method_found": gnaf_plan is not None,
            "gnaf_plan_correct": gnaf_plan_match,
            "spatial_method_lotplan": spatial_lotplan,
            "spatial_method_area_sqm": spatial_area,
            "spatial_method_found": spatial_plan is not None,
            "spatial_plan_matches_gnaf": spatial_plan_match,
            "methods_agree": methods_agree,
            "spatial_is_parent_lot": spatial_is_parent,
        })

        status = "AGREE" if methods_agree else "DIFFER"
        if not gnaf_plan:
            status = "GNAF_MISS"
        if not spatial_plan:
            status = "SPATIAL_MISS"
        print(f"  [{i:2d}/{len(addresses)}] {status:13s} {display[:60]}")

    # Write CSV
    fieldnames = list(results[0].keys())
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Summary
    total = len(results)
    gnaf_found = sum(1 for r in results if r["gnaf_method_found"])
    spatial_found = sum(1 for r in results if r["spatial_method_found"])
    both_agree = sum(1 for r in results if r["methods_agree"])
    gnaf_correct = sum(1 for r in results if r["gnaf_plan_correct"])
    spatial_parent = sum(1 for r in results if r["spatial_is_parent_lot"])

    print(f"\n{'='*60}")
    print(f"SUMMARY ({total} addresses)")
    print(f"{'='*60}")
    print(f"  GNAF text method found a result:   {gnaf_found:3d}/{total}")
    print(f"  GNAF text method correct plan:     {gnaf_correct:3d}/{total}")
    print(f"  Spatial method found a result:      {spatial_found:3d}/{total}")
    print(f"  Methods agree (same lot/plan):      {both_agree:3d}/{total}")
    print(f"  Spatial returned a parent lot:      {spatial_parent:3d}/{total}")
    print(f"\nReport written to: {OUTPUT_CSV}")

    conn.close()


if __name__ == "__main__":
    main()
