#!/usr/bin/env python3
"""
Import GNAF (Geocoded National Address File) PSV data into PostgreSQL.

Imports the four tables used by the app:
  gnaf_state, gnaf_locality, gnaf_address_detail, gnaf_address_site_geocode

Usage:
    python import_gnaf.py --data-dir /path/to/gnaf-release
    python import_gnaf.py --data-dir db/data/gnaf/g-naf_feb26_allstates_gda2020_psv_1022
    python import_gnaf.py --data-dir ... --truncate

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

TABLE_MAP = {
    "state":                "gnaf_state",
    "locality":             "gnaf_locality",
    "address_detail":       "gnaf_address_detail",
    "address_site_geocode": "gnaf_address_site_geocode",
}

# Import order matters — FK dependencies must load first
IMPORT_ORDER = ["state", "locality", "address_detail", "address_site_geocode"]

# Filename suffixes to classify PSV files — must match {STATE}_{TABLE}_psv.psv exactly.
# Uses endswith check (not substring) to avoid matching LOCALITY_ALIAS, LOCALITY_NEIGHBOUR, etc.
TABLE_PATTERNS = [
    ("address_site_geocode", "_ADDRESS_SITE_GEOCODE_psv.psv"),
    ("address_detail",       "_ADDRESS_DETAIL_psv.psv"),
    ("locality",             "_LOCALITY_psv.psv"),
    ("state",                "_STATE_psv.psv"),
]

# Explicit column list for COPY where the table has extra columns not in the PSV.
# gnaf_address_site_geocode has a 'geometry' column that is populated separately
# via UPDATE after the COPY — it must be excluded from the COPY column list.
COPY_COLUMNS = {
    "gnaf_address_site_geocode": (
        "address_site_geocode_pid, date_created, date_retired, address_site_pid, "
        "geocode_site_name, geocode_site_description, geocode_type_code, "
        "reliability_code, boundary_extent, planimetric_accuracy, elevation, "
        "longitude, latitude"
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

def classify_psv(path: Path) -> str | None:
    name = path.name
    for key, pattern in TABLE_PATTERNS:
        if name.endswith(pattern):
            # Exclude {STATE}_STREET_LOCALITY_psv.psv from matching locality
            prefix = name[: -len(pattern)]
            if "STREET" in prefix.upper():
                continue
            return key
    return None


def find_psv_files(data_dir: str) -> dict[str, list[Path]]:
    """Recursively find all relevant PSV files, grouped by table key."""
    result: dict[str, list[Path]] = {k: [] for k in IMPORT_ORDER}
    for psv in sorted(Path(data_dir).rglob("*.psv")):
        key = classify_psv(psv)
        if key is not None:
            result[key].append(psv)
    return result


# ─── Import ──────────────────────────────────────────────────────────────────

def import_psv_file(cur, table: str, path: Path) -> None:
    cols = COPY_COLUMNS.get(table, "")
    col_clause = f"({cols})" if cols else ""
    sql = f"COPY {table} {col_clause} FROM STDIN WITH (FORMAT CSV, DELIMITER '|', HEADER TRUE)"
    with open(path, "r", encoding="utf-8") as f:
        cur.copy_expert(sql, f)


def truncate_tables(conn):
    log.info("Truncating GNAF tables (reverse FK order)...")
    with conn.cursor() as cur:
        for key in reversed(IMPORT_ORDER):
            cur.execute(f"TRUNCATE {TABLE_MAP[key]} CASCADE")
            log.info(f"  Truncated {TABLE_MAP[key]}")
    conn.commit()


def populate_geocode_geometry(conn):
    """Populate geometry column from longitude/latitude after COPY."""
    log.info("Populating geometry from longitude/latitude...")
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE gnaf_address_site_geocode
            SET geometry = ST_SetSRID(ST_MakePoint(longitude, latitude), 7844)
            WHERE longitude IS NOT NULL
              AND latitude  IS NOT NULL
              AND geometry  IS NULL
        """)
        log.info(f"  Updated {cur.rowcount:,} rows")
    conn.commit()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import GNAF PSV files into PostgreSQL")
    parser.add_argument("--data-dir", required=True,
                        help="Root directory of GNAF release (contains G-NAF/)")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate existing GNAF tables before importing")
    args = parser.parse_args()

    if not Path(args.data_dir).exists():
        log.error(f"Directory not found: {args.data_dir}")
        sys.exit(1)

    log.info(f"Scanning {args.data_dir} for PSV files...")
    files = find_psv_files(args.data_dir)

    if not any(files.values()):
        log.error("No PSV files found. Check --data-dir points to the GNAF release root.")
        sys.exit(1)

    for key in IMPORT_ORDER:
        log.info(f"  {TABLE_MAP[key]}: {len(files[key])} file(s)")

    conn = get_connection()
    try:
        if args.truncate:
            truncate_tables(conn)

        # Defer FK constraint checks during bulk load for performance
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica")

        for key in IMPORT_ORDER:
            table = TABLE_MAP[key]
            psv_list = files[key]
            if not psv_list:
                log.warning(f"No files found for {table} — skipping")
                continue

            log.info(f"Importing {table} ({len(psv_list)} file(s))...")
            with conn.cursor() as cur:
                for i, path in enumerate(psv_list, 1):
                    import_psv_file(cur, table, path)
                    if i % 5 == 0 or i == len(psv_list):
                        log.info(f"  {i}/{len(psv_list)} files done")
            conn.commit()
            log.info(f"  {table} committed")

        # Re-enable FK checks
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = DEFAULT")
        conn.commit()

        populate_geocode_geometry(conn)

        log.info("Row counts:")
        with conn.cursor() as cur:
            for key in IMPORT_ORDER:
                cur.execute(f"SELECT COUNT(*) FROM {TABLE_MAP[key]}")
                log.info(f"  {TABLE_MAP[key]}: {cur.fetchone()[0]:,}")

        log.info("GNAF import complete.")

    except Exception:
        conn.rollback()
        log.exception("Import failed — rolled back")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
