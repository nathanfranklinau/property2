#!/usr/bin/env python3
"""
Import Gold Coast City Plan Version 13 layers from the ArcGIS Feature Service.

Downloads selected layers via the REST API with pagination and inserts them into
PostgreSQL tables prefixed with qld_goldcoast_.

Usage:
    # Import all layers (truncates first — recommended):
    python import_goldcoast_cityplan.py --truncate

    # Import specific layers only:
    python import_goldcoast_cityplan.py --layers 4 33 35 --truncate

    # List available layers:
    python import_goldcoast_cityplan.py --list-layers

    # Slower pace if worried about rate limits:
    python import_goldcoast_cityplan.py --truncate --delay 1.0

Source:
    Gold Coast City Plan Version 13 — Open Data
    https://data-goldcoast.opendata.arcgis.com/maps/0ec7b75a2a794e8eb71c12720c008332/about
    License: CC BY 4.0

Prerequisites:
    pip install requests psycopg2-binary python-dotenv tqdm
"""

import json
import os
import sys
import logging
import argparse
import time

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE_URL = (
    "https://services-ap1.arcgis.com/lnVW0dLI3fvST2hd/arcgis/rest/services"
    "/City_Plan_Version_13_Open_Data/FeatureServer"
)

# layer_id → {table, description, fields: [(api_field, pg_column), ...]}
# Fields are (ArcGIS name, PostgreSQL column name).
# Omitted: OBJECTID, created_*/last_edited_* (ArcGIS internals), Shape__Area/Length (computable from geometry).
LAYERS = {
    4: {
        "table": "qld_goldcoast_zones",
        "description": "Zone",
        "fields": [
            ("ZONE_PRECINCT",   "zone_precinct"),
            ("LVL1_ZONE",       "lvl1_zone"),
            ("LGA_CODE",        "lga_code"),
            ("ZONE",            "zone"),
            ("Building_height", "building_height"),
            ("BH_Category",     "bh_category"),
        ],
    },
    33: {
        "table": "qld_goldcoast_building_height",
        "description": "Building height boundary",
        "fields": [
            ("LGA_CODE",         "lga_code"),
            ("CAT_DESC",         "cat_desc"),
            ("OVL_CAT",          "ovl_cat"),
            ("OVL2_DESC",        "ovl2_desc"),
            ("OVL2_CAT",         "ovl2_cat"),
            ("HEIGHT_IN_METRES", "height_in_metres"),
            ("STOREY_NUMBER",    "storey_number"),
            ("LABEL",            "label"),
            ("HEIGHT_LABEL",     "height_label"),
        ],
    },
    35: {
        "table": "qld_goldcoast_bushfire_hazard",
        "description": "Bushfire hazard area",
        "fields": [
            ("LGA_CODE",  "lga_code"),
            ("CAT_DESC",  "cat_desc"),
            ("OVL_CAT",   "ovl_cat"),
            ("OVL2_DESC", "ovl2_desc"),
            ("OVL2_CAT",  "ovl2_cat"),
        ],
    },
    43: {
        "table": "qld_goldcoast_dwelling_house_overlay",
        "description": "Dwelling house overlay area",
        "fields": [
            ("LGA_CODE",  "lga_code"),
            ("CAT_DESC",  "cat_desc"),
            ("OVL_CAT",   "ovl_cat"),
            ("OVL2_DESC", "ovl2_desc"),
            ("OVL2_CAT",  "ovl2_cat"),
        ],
    },
    73: {
        "table": "qld_goldcoast_buffer_area",
        "description": "Buffer area",
        "fields": [],  # no attribute fields beyond geometry
    },
    94: {
        "table": "qld_goldcoast_airport_noise",
        "description": "Airport noise exposure area",
        "fields": [
            ("LGA_CODE",           "lga_code"),
            ("CAT_DESC",           "cat_desc"),
            ("OVL_CAT",            "ovl_cat"),
            ("OVL2_DESC",          "ovl2_desc"),
            ("OVL2_CAT",           "ovl2_cat"),
            ("SENSITIVE_USE_TYPE", "sensitive_use_type"),
            ("BUFFER_SOURCE",      "buffer_source"),
            ("BUFFER_DISTANCE",    "buffer_distance"),
        ],
    },
    101: {
        "table": "qld_goldcoast_minimum_lot_size",
        "description": "Minimum lot size",
        "fields": [
            ("LGA_CODE",  "lga_code"),
            ("CAT_DESC",  "cat_desc"),
            ("OVL_CAT",   "ovl_cat"),
            ("OVL2_DESC", "ovl2_desc"),
            ("OVL2_CAT",  "ovl2_cat"),
            ("MLS",       "mls"),
        ],
    },
    105: {
        "table": "qld_goldcoast_party_house",
        "description": "Party house area",
        "fields": [
            ("LGA_CODE",  "lga_code"),
            ("CAT_DESC",  "cat_desc"),
            ("OVL_CAT",   "ovl_cat"),
            ("OVL2_DESC", "ovl2_desc"),
            ("OVL2_CAT",  "ovl2_cat"),
        ],
    },
    115: {
        "table": "qld_goldcoast_residential_density",
        "description": "Residential density",
        "fields": [
            ("LGA_CODE",             "lga_code"),
            ("CAT_DESC",             "cat_desc"),
            ("OVL_CAT",              "ovl_cat"),
            ("OVL2_DESC",            "ovl2_desc"),
            ("OVL2_CAT",             "ovl2_cat"),
            ("RESIDENTIAL_DENSITY",  "residential_density"),
        ],
    },
    81: {
        "table": "qld_goldcoast_flood",
        "description": "Flood assessment required",
        "fields": [
            ("LGA_CODE",  "lga_code"),
            ("CAT_DESC",  "cat_desc"),
            ("OVL_CAT",   "ovl_cat"),
            ("OVL2_DESC", "ovl2_desc"),
            ("OVL2_CAT",  "ovl2_cat"),
        ],
    },
    83: {
        "table": "qld_goldcoast_heritage",
        "description": "Heritage place",
        "fields": [
            ("LGA_CODE",                    "lga_code"),
            ("CAT_DESC",                    "cat_desc"),
            ("OVL_CAT",                     "ovl_cat"),
            ("OVL2_DESC",                   "ovl2_desc"),
            ("OVL2_CAT",                    "ovl2_cat"),
            ("LHR_ID",                      "lhr_id"),
            ("PLACE_NAME",                  "place_name"),
            ("ASSESSMENT_ID",               "assessment_id"),
            ("REGISTER_STATUS",             "register_status"),
            ("QLD_HERITAGE_REGISTER",       "qld_heritage_register"),
            ("HERITAGE_PROTECTION_BOUNDARY","heritage_protection_boundary"),
            ("ADJOINING_ALLOTMENTS",        "adjoining_allotments"),
        ],
    },
    84: {
        "table": "qld_goldcoast_heritage_proximity",
        "description": "Place in proximity to a local heritage place",
        "fields": [
            ("LGA_CODE",              "lga_code"),
            ("CAT_DESC",              "cat_desc"),
            ("OVL_CAT",               "ovl_cat"),
            ("OVL2_DESC",             "ovl2_desc"),
            ("OVL2_CAT",              "ovl2_cat"),
            ("LHR_ID",                "lhr_id"),
            ("LOT_PLAN",              "lot_plan"),
            ("ASSESSMENT_ID",         "assessment_id"),
            ("PLACE_NAME",            "place_name"),
            ("QLD_HERITAGE_REGISTER", "qld_heritage_register"),
        ],
    },
}

# Environmental significance sub-layers → single qld_goldcoast_environmental table.
# Each layer is imported with a static 'category' column value.
ENVIRONMENTAL_LAYERS = {
    48: "Coastal wetlands & islands core habitat",
    49: "Hinterland core habitat",
    50: "Substantial remnants",
    51: "Hinterland to coast critical corridors",
    54: "State significant species",
    55: "Koala habitat areas",
    57: "Local significant species",
    60: "Regulated vegetation",
    66: "State significant wetlands & aquatic systems",
    68: "Local significant wetlands",
}

# How many features to request per page. Service maxRecordCount is 2000;
# 1000 is conservative — smaller responses, less risk of timeouts.
PAGE_SIZE = 1000

MAX_RETRIES = 4
RETRY_BASE_WAIT = 5  # seconds; doubles each retry


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "realestatev2"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "PropertyProfiler/1.0 (open data import)",
        "Accept": "application/json",
    })
    return s


def fetch_with_retry(session: requests.Session, url: str, params: dict, delay: float) -> dict:
    """GET with exponential backoff on 429/503 and network errors."""
    wait = RETRY_BASE_WAIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=60)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Request failed after {MAX_RETRIES} attempts: {exc}") from exc
            log.warning(f"  Network error (attempt {attempt}/{MAX_RETRIES}): {exc} — retrying in {wait}s")
            time.sleep(wait)
            wait *= 2
            continue

        if resp.status_code == 200:
            time.sleep(delay)
            return resp.json()

        if resp.status_code in (429, 503):
            retry_after = int(resp.headers.get("Retry-After", wait))
            log.warning(f"  HTTP {resp.status_code} (attempt {attempt}/{MAX_RETRIES}) — waiting {retry_after}s")
            time.sleep(retry_after)
            wait = max(wait * 2, retry_after + 1)
            continue

        resp.raise_for_status()

    raise RuntimeError(f"Exhausted retries for {url}")


def get_feature_count(session: requests.Session, layer_id: int, delay: float) -> int:
    data = fetch_with_retry(
        session,
        f"{BASE_URL}/{layer_id}/query",
        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
        delay,
    )
    return data.get("count", 0)


def fetch_page(session: requests.Session, layer_id: int, offset: int, delay: float) -> dict:
    return fetch_with_retry(
        session,
        f"{BASE_URL}/{layer_id}/query",
        {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "outSR": "4326",        # WGS84 lon/lat; PostGIS transforms to 7844 on insert
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
        },
        delay,
    )


def insert_features(conn, table: str, fields: list, features: list, extra_cols: dict | None = None):
    """Bulk-insert a page of GeoJSON features into the target table.

    extra_cols: optional dict of {column_name: static_value} to add to every row.
    """
    if not features:
        return

    pg_cols = [pg_col for _, pg_col in fields]
    extra_names = list((extra_cols or {}).keys())
    all_cols = extra_names + pg_cols
    col_list = ", ".join(all_cols + ["geometry"]) if all_cols else "geometry"

    # Build parameterized placeholders
    attr_placeholders = ", ".join(["%s"] * len(all_cols))
    geom_expr = "ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 7844)"

    if all_cols:
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({attr_placeholders}, {geom_expr})"
    else:
        sql = f"INSERT INTO {table} (geometry) VALUES ({geom_expr})"

    extra_vals = list((extra_cols or {}).values())
    rows = []
    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry")
        geom_str = json.dumps(geom) if geom else None

        attr_vals = [props.get(api_field) for api_field, _ in fields]
        rows.append(tuple(extra_vals + attr_vals) + (geom_str,))

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()


def truncate_table(conn, table: str):
    log.info(f"  Truncating {table}...")
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {table}")
    conn.commit()


def import_layer(session, conn, layer_id: int, layer: dict, truncate: bool, delay: float):
    table = layer["table"]
    description = layer["description"]
    fields = layer["fields"]

    log.info(f"Layer {layer_id}: {description} → {table}")

    if truncate:
        truncate_table(conn, table)

    total = get_feature_count(session, layer_id, delay)
    log.info(f"  Total features: {total:,}")

    if total == 0:
        log.warning("  No features returned — skipping.")
        return

    offset = 0
    with tqdm(total=total, unit="feat", desc=f"  Layer {layer_id}") as pbar:
        while True:
            page = fetch_page(session, layer_id, offset, delay)
            features = page.get("features", [])
            if not features:
                break

            insert_features(conn, table, fields, features)
            offset += len(features)
            pbar.update(len(features))

            # Stop when we receive fewer features than requested — last page.
            # (Don't rely on exceededTransferLimit — not always present in GeoJSON responses.)
            if len(features) < PAGE_SIZE:
                break

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        db_count = cur.fetchone()[0]
    log.info(f"  Done — {db_count:,} rows in {table}")


def import_environmental_layer(session, conn, layer_id: int, category: str, delay: float):
    """Import a single environmental significance sub-layer into the consolidated table."""
    table = "qld_goldcoast_environmental"
    fields = [
        ("LGA_CODE",  "lga_code"),
        ("CAT_DESC",  "cat_desc"),
        ("OVL_CAT",   "ovl_cat"),
        ("OVL2_DESC", "ovl2_desc"),
        ("OVL2_CAT",  "ovl2_cat"),
    ]

    log.info(f"Environmental layer {layer_id}: {category}")

    total = get_feature_count(session, layer_id, delay)
    log.info(f"  Total features: {total:,}")
    if total == 0:
        log.warning("  No features — skipping.")
        return

    offset = 0
    with tqdm(total=total, unit="feat", desc=f"  Env {layer_id}") as pbar:
        while True:
            page = fetch_page(session, layer_id, offset, delay)
            features = page.get("features", [])
            if not features:
                break
            insert_features(conn, table, fields, features, extra_cols={"category": category})
            offset += len(features)
            pbar.update(len(features))
            if len(features) < PAGE_SIZE:
                break


def list_layers():
    print(f"\nAvailable layers ({BASE_URL}):\n")
    print(f"  {'ID':>4}  {'Table':<45}  Description")
    print(f"  {'--':>4}  {'-----':<45}  -----------")
    for layer_id, layer in sorted(LAYERS.items()):
        print(f"  {layer_id:>4}  {layer['table']:<45}  {layer['description']}")
    print(f"\n  Environmental significance sub-layers → qld_goldcoast_environmental:")
    for layer_id, category in sorted(ENVIRONMENTAL_LAYERS.items()):
        print(f"  {layer_id:>4}  {'qld_goldcoast_environmental':<45}  {category}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Import Gold Coast City Plan layers from ArcGIS into PostgreSQL"
    )
    parser.add_argument(
        "--layers", nargs="+", type=int, metavar="ID",
        help="Layer IDs to import (default: all). E.g. --layers 4 33 35",
    )
    parser.add_argument(
        "--truncate", action="store_true", default=False,
        help="Truncate each target table before importing (recommended for fresh runs)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.5, metavar="SECS",
        help="Seconds to wait between HTTP requests (default: 0.5)",
    )
    parser.add_argument(
        "--list-layers", action="store_true",
        help="Print available layers and exit",
    )
    args = parser.parse_args()

    if args.list_layers:
        list_layers()
        sys.exit(0)

    all_known = set(LAYERS.keys()) | set(ENVIRONMENTAL_LAYERS.keys())
    target_ids = args.layers if args.layers else sorted(all_known)
    unknown = [lid for lid in target_ids if lid not in all_known]
    if unknown:
        log.error(f"Unknown layer IDs: {unknown}. Run --list-layers to see valid IDs.")
        sys.exit(1)

    session = make_session()
    conn = get_connection()

    try:
        # Truncate environmental table once if any env layers are targeted
        env_targeted = [lid for lid in target_ids if lid in ENVIRONMENTAL_LAYERS]
        if args.truncate and env_targeted:
            truncate_table(conn, "qld_goldcoast_environmental")

        for layer_id in target_ids:
            if layer_id in LAYERS:
                import_layer(session, conn, layer_id, LAYERS[layer_id], args.truncate, args.delay)
            elif layer_id in ENVIRONMENTAL_LAYERS:
                import_environmental_layer(session, conn, layer_id, ENVIRONMENTAL_LAYERS[layer_id], args.delay)

        log.info("Gold Coast City Plan import complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
