#!/usr/bin/env python3
"""
Import the QLD registered pools CSV into qld_pools_registered.

The CSV file is available from the Queensland Government open data portal:
    https://www.data.qld.gov.au/dataset/register-of-swimming-pools

Usage:
    python import_qld_pools.py --csv /path/to/PoolsRegister.csv
    python import_qld_pools.py --csv /path/to/PoolsRegister.csv --truncate

The CSV is encoded UTF-16 (as supplied by QLD Gov). This script handles that.
"""

import os
import csv
import sys
import logging
import argparse
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# CSV column name → DB column name
COLUMN_MAP = {
    "Site Name":                     "site_name",
    "Unit Number":                   "unit_number",
    "Street Number":                 "street_number",
    "Street Name":                   "street_name",
    "Street Type":                   "street_type",
    "Suburb":                        "suburb",
    "Post Code":                     "postcode",
    "Number of Pools":               "number_of_pools",
    "Local Government Authority Area": "lga",
    "Shared Pool Property":          "shared_pool_property",
}

BATCH_SIZE = 5000


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def read_rows(csv_path: str) -> list[dict]:
    """Read the CSV, normalising column names and values."""
    rows = []
    # QLD pools CSV is UTF-16 encoded
    with open(csv_path, "r", encoding="utf-16") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            site_name = (raw.get("Site Name") or "").strip()
            if not site_name:
                continue  # skip blank rows

            row = {}
            for csv_col, db_col in COLUMN_MAP.items():
                val = (raw.get(csv_col) or "").strip() or None
                row[db_col] = val

            # Type coercions
            if row["number_of_pools"] is not None:
                try:
                    row["number_of_pools"] = int(row["number_of_pools"])
                except ValueError:
                    row["number_of_pools"] = None

            rows.append(row)

    return rows


def upsert_rows(conn, rows: list[dict]):
    """Upsert all rows into qld_pools_registered in batches."""
    cols = list(COLUMN_MAP.values())
    placeholders = ", ".join(f"%({c})s" for c in cols)
    col_list = ", ".join(cols)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "site_name")

    sql = f"""
        INSERT INTO qld_pools_registered ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (site_name)
        DO UPDATE SET {update_set}
    """

    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
            total += len(batch)
            conn.commit()
            log.info(f"  {total:,} / {len(rows):,} rows upserted")

    return total


def main():
    parser = argparse.ArgumentParser(description="Import QLD pools CSV into PostgreSQL")
    parser.add_argument("--csv", required=True, help="Path to QLD pools register CSV")
    parser.add_argument(
        "--truncate",
        action="store_true",
        default=False,
        help="Truncate qld_pools_registered before importing",
    )
    args = parser.parse_args()

    if not Path(args.csv).exists():
        log.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    log.info(f"Reading {args.csv}...")
    rows = read_rows(args.csv)
    log.info(f"  {len(rows):,} rows to import")

    conn = get_connection()
    try:
        if args.truncate:
            log.info("Truncating qld_pools_registered...")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE qld_pools_registered")
            conn.commit()

        log.info("Upserting rows...")
        total = upsert_rows(conn, rows)
        log.info(f"QLD pools import complete: {total:,} rows.")

    except Exception:
        conn.rollback()
        log.exception("Import failed — rolled back")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
