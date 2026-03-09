#!/usr/bin/env python3
"""
Import the FULL GNAF (Geocoded National Address File) dataset into PostgreSQL.

Loads all 35 tables (16 authority code + 19 standard per-state) into gnaf_data_* tables.

Usage:
    python import/import_gnaf_full.py --data-dir /path/to/gnaf-release
    python import/import_gnaf_full.py --data-dir /path/to/gnaf-release --truncate

The --data-dir should point to the top-level release folder containing the G-NAF/ directory.
Example:
    python import/import_gnaf_full.py \\
        --data-dir /path/to/g-naf_feb26_allstates_gda2020_psv_1022

GNAF releases: https://data.gov.au/dataset/geocoded-national-address-file-g-naf
"""

import os
import sys
import logging
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Table configuration ─────────────────────────────────────────────────────

# Authority code tables — one file each, no state prefix.
# Map: PSV filename stem (after "Authority_Code_") → DB table name
AUTHORITY_TABLES = {
    "ADDRESS_ALIAS_TYPE_AUT":          "gnaf_data_address_alias_type_aut",
    "ADDRESS_CHANGE_TYPE_AUT":         "gnaf_data_address_change_type_aut",
    "ADDRESS_TYPE_AUT":                "gnaf_data_address_type_aut",
    "FLAT_TYPE_AUT":                   "gnaf_data_flat_type_aut",
    "GEOCODED_LEVEL_TYPE_AUT":         "gnaf_data_geocoded_level_type_aut",
    "GEOCODE_RELIABILITY_AUT":         "gnaf_data_geocode_reliability_aut",
    "GEOCODE_TYPE_AUT":                "gnaf_data_geocode_type_aut",
    "LEVEL_TYPE_AUT":                  "gnaf_data_level_type_aut",
    "LOCALITY_ALIAS_TYPE_AUT":         "gnaf_data_locality_alias_type_aut",
    "LOCALITY_CLASS_AUT":              "gnaf_data_locality_class_aut",
    "MB_MATCH_CODE_AUT":               "gnaf_data_mb_match_code_aut",
    "PS_JOIN_TYPE_AUT":                "gnaf_data_ps_join_type_aut",
    "STREET_CLASS_AUT":                "gnaf_data_street_class_aut",
    "STREET_LOCALITY_ALIAS_TYPE_AUT":  "gnaf_data_street_locality_alias_type_aut",
    "STREET_SUFFIX_AUT":               "gnaf_data_street_suffix_aut",
    "STREET_TYPE_AUT":                 "gnaf_data_street_type_aut",
}

# Standard tables — one file per state per table.
# Ordered for FK-safe loading (parents before children).
# Map: PSV filename suffix (after "{STATE}_") → DB table name
# Matching uses endswith to avoid ambiguity (e.g. LOCALITY vs STREET_LOCALITY).
STANDARD_TABLES_ORDERED = [
    # Level 0 — no FK deps on other standard tables
    ("STATE",                    "gnaf_data_state"),
    ("MB_2016",                  "gnaf_data_mb_2016"),
    ("MB_2021",                  "gnaf_data_mb_2021"),
    # Level 1 — depends on state
    ("LOCALITY",                 "gnaf_data_locality"),
    # Level 2 — depends on locality
    ("LOCALITY_ALIAS",           "gnaf_data_locality_alias"),
    ("LOCALITY_NEIGHBOUR",       "gnaf_data_locality_neighbour"),
    ("LOCALITY_POINT",           "gnaf_data_locality_point"),
    ("STREET_LOCALITY",          "gnaf_data_street_locality"),
    # Level 3 — depends on street_locality
    ("STREET_LOCALITY_ALIAS",    "gnaf_data_street_locality_alias"),
    ("STREET_LOCALITY_POINT",    "gnaf_data_street_locality_point"),
    # Level 4 — address site (no standard-table FK)
    ("ADDRESS_SITE",             "gnaf_data_address_site"),
    # Level 5 — depends on address_site, locality, street_locality
    ("ADDRESS_DETAIL",           "gnaf_data_address_detail"),
    # Level 6 — depends on address_site or address_detail
    ("ADDRESS_SITE_GEOCODE",     "gnaf_data_address_site_geocode"),
    ("ADDRESS_DEFAULT_GEOCODE",  "gnaf_data_address_default_geocode"),
    ("ADDRESS_ALIAS",            "gnaf_data_address_alias"),
    ("ADDRESS_FEATURE",          "gnaf_data_address_feature"),
    ("ADDRESS_MESH_BLOCK_2016",  "gnaf_data_address_mesh_block_2016"),
    ("ADDRESS_MESH_BLOCK_2021",  "gnaf_data_address_mesh_block_2021"),
    ("PRIMARY_SECONDARY",        "gnaf_data_primary_secondary"),
]

# Tables with extra columns not in PSV — must specify COPY column list
COPY_COLUMNS = {
    "gnaf_data_address_site_geocode": (
        "address_site_geocode_pid, date_created, date_retired, address_site_pid, "
        "geocode_site_name, geocode_site_description, geocode_type_code, "
        "reliability_code, boundary_extent, planimetric_accuracy, elevation, "
        "longitude, latitude"
    ),
    "gnaf_data_address_default_geocode": (
        "address_default_geocode_pid, date_created, date_retired, "
        "address_detail_pid, geocode_type_code, longitude, latitude"
    ),
}


# ─── Database ────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


# ─── File discovery ──────────────────────────────────────────────────────────

def find_authority_files(data_dir: Path) -> dict[str, Path]:
    """Find authority code PSV files. Returns {table_key: path}."""
    result = {}
    for psv in sorted(data_dir.rglob("Authority_Code_*_psv.psv")):
        # Extract table key: "Authority_Code_FLAT_TYPE_AUT_psv.psv" → "FLAT_TYPE_AUT"
        stem = psv.stem  # "Authority_Code_FLAT_TYPE_AUT_psv"
        key = stem.replace("Authority_Code_", "").replace("_psv", "")
        if key in AUTHORITY_TABLES:
            result[key] = psv
    return result


def find_standard_files(data_dir: Path) -> dict[str, list[Path]]:
    """Find per-state standard PSV files. Returns {table_key: [paths]}."""
    result: dict[str, list[Path]] = {key: [] for key, _ in STANDARD_TABLES_ORDERED}

    # Collect all standard PSV files
    standard_psvs = sorted(
        p for p in data_dir.rglob("*.psv")
        if "Authority_Code" not in p.name
    )

    for psv in standard_psvs:
        stem = psv.stem  # e.g. "QLD_ADDRESS_DETAIL_psv"
        name_no_suffix = stem.replace("_psv", "")  # "QLD_ADDRESS_DETAIL"

        # Try to match against each table key (longest match first to avoid ambiguity)
        matched = False
        for table_key, _ in sorted(STANDARD_TABLES_ORDERED, key=lambda x: -len(x[0])):
            suffix = f"_{table_key}"
            if name_no_suffix.endswith(suffix):
                # Verify the prefix is a valid state code (2-3 chars)
                prefix = name_no_suffix[: -len(suffix)]
                if 1 <= len(prefix) <= 3:
                    result[table_key].append(psv)
                    matched = True
                    break

    return result


# ─── Import ──────────────────────────────────────────────────────────────────

def import_psv_file(cur, table: str, path: Path) -> int:
    """COPY a single PSV file into a table. Returns row count."""
    cols = COPY_COLUMNS.get(table, "")
    col_clause = f"({cols})" if cols else ""
    sql = f"COPY {table} {col_clause} FROM STDIN WITH (FORMAT CSV, DELIMITER '|', HEADER TRUE)"
    with open(path, "r", encoding="utf-8") as f:
        cur.copy_expert(sql, f)
    return cur.rowcount


def populate_geometry(conn, table: str, label: str):
    """Populate geometry column from longitude/latitude after COPY."""
    log.info(f"Populating geometry for {label}...")
    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE {table}
            SET geometry = ST_SetSRID(ST_MakePoint(longitude, latitude), 7844)
            WHERE longitude IS NOT NULL
              AND latitude  IS NOT NULL
              AND geometry  IS NULL
        """)
        log.info(f"  Updated {cur.rowcount:,} rows")
    conn.commit()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import full GNAF dataset into PostgreSQL")
    parser.add_argument("--data-dir", required=True,
                        help="Root directory of GNAF release (contains G-NAF/)")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate all gnaf_data_* tables before importing")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        log.error(f"Directory not found: {data_dir}")
        sys.exit(1)

    # ── Discover files ──
    log.info(f"Scanning {data_dir} for PSV files...")
    auth_files = find_authority_files(data_dir)
    std_files = find_standard_files(data_dir)

    log.info(f"Authority code tables: {len(auth_files)}/{len(AUTHORITY_TABLES)} found")
    for key in sorted(AUTHORITY_TABLES):
        status = "OK" if key in auth_files else "MISSING"
        log.info(f"  {AUTHORITY_TABLES[key]}: {status}")

    log.info(f"Standard tables:")
    for key, table in STANDARD_TABLES_ORDERED:
        log.info(f"  {table}: {len(std_files[key])} state file(s)")

    if not auth_files and not any(std_files.values()):
        log.error("No PSV files found. Check --data-dir points to the GNAF release root.")
        sys.exit(1)

    conn = get_connection()
    try:
        # ── Truncate ──
        if args.truncate:
            log.info("Truncating gnaf_data_* tables...")
            with conn.cursor() as cur:
                # Reverse order for FK safety
                for key, table in reversed(STANDARD_TABLES_ORDERED):
                    cur.execute(f"TRUNCATE {table} CASCADE")
                for key in AUTHORITY_TABLES:
                    cur.execute(f"TRUNCATE {AUTHORITY_TABLES[key]} CASCADE")
            conn.commit()
            log.info("  All gnaf_data_* tables truncated")

        # Defer FK constraint checks during bulk load
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica")

        # ── Import authority code tables ──
        log.info("═══ Importing authority code tables ═══")
        for key in sorted(AUTHORITY_TABLES):
            table = AUTHORITY_TABLES[key]
            if key not in auth_files:
                log.warning(f"  Skipping {table} — file not found")
                continue
            with conn.cursor() as cur:
                rows = import_psv_file(cur, table, auth_files[key])
                log.info(f"  {table}: {rows:,} rows")
            conn.commit()

        # ── Import standard tables (FK order) ──
        log.info("═══ Importing standard tables ═══")
        for key, table in STANDARD_TABLES_ORDERED:
            psv_list = std_files[key]
            if not psv_list:
                log.warning(f"  Skipping {table} — no files found")
                continue

            log.info(f"Importing {table} ({len(psv_list)} file(s))...")
            total_rows = 0
            with conn.cursor() as cur:
                for i, path in enumerate(psv_list, 1):
                    rows = import_psv_file(cur, table, path)
                    total_rows += rows
                    if i % 3 == 0 or i == len(psv_list):
                        log.info(f"  {i}/{len(psv_list)} files done ({total_rows:,} rows so far)")
            conn.commit()
            log.info(f"  {table}: {total_rows:,} rows total")

        # Re-enable FK checks
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = DEFAULT")
        conn.commit()

        # ── Populate geometry columns ──
        populate_geometry(conn, "gnaf_data_address_site_geocode", "address_site_geocode")
        populate_geometry(conn, "gnaf_data_address_default_geocode", "address_default_geocode")

        # ── Final row counts ──
        log.info("═══ Final row counts ═══")
        with conn.cursor() as cur:
            for key in sorted(AUTHORITY_TABLES):
                table = AUTHORITY_TABLES[key]
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                log.info(f"  {table}: {cur.fetchone()[0]:,}")
            for key, table in STANDARD_TABLES_ORDERED:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                log.info(f"  {table}: {cur.fetchone()[0]:,}")

        log.info("GNAF full import complete.")

    except Exception:
        conn.rollback()
        log.exception("Import failed — rolled back")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
