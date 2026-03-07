#!/usr/bin/env python3
"""
Import the QLD DCDB (Digital Cadastral Database) File Geodatabase into PostgreSQL.

Uses ogr2ogr (bundled with GDAL) to load the QLD_CADASTRE_DCDB layer.

Usage:
    python import_qld_cadastre.py --gdb /path/to/DP_QLD_DCDB_WOS_CUR_GDA2020.gdb
    python import_qld_cadastre.py --gdb db/data/cadastre/qld/DP_QLD_DCDB_WOS_CUR_GDA2020.gdb
    python import_qld_cadastre.py --gdb ... --truncate
    python import_qld_cadastre.py --gdb ... --list-layers

Source:
    https://www.data.qld.gov.au/dataset/queensland-cadastral-data

Prerequisites:
    GDAL with OpenFileGDB driver (included in: brew install gdal)
    Confirm: ogrinfo <file.gdb>
"""

import os
import sys
import logging
import argparse
import subprocess
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


# GDB layer containing the main cadastre parcels (MultiPolygon)
PARCELS_LAYER = "QLD_CADASTRE_DCDB"

# SQL to select and rename fields from source → our table columns.
# Confirmed field names from: ogrinfo -al -so <file.gdb> QLD_CADASTRE_DCDB
# Source fields: LOT, PLAN, LOTPLAN, LOT_AREA, EXCL_AREA
SELECT_SQL = (
    'SELECT "LOT" AS lot, "PLAN" AS plan, "LOTPLAN" AS lotplan, '
    '"LOT_AREA" AS lot_area, "EXCL_AREA" AS excl_area '
    f'FROM "{PARCELS_LAYER}"'
)


def pg_dsn() -> str:
    return (
        f"PG:host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'subdivide')} "
        f"user={os.getenv('POSTGRES_USER', '')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def list_layers(gdb: str):
    result = subprocess.run(["ogrinfo", "-al", "-so", gdb], capture_output=True, text=True)
    print(result.stdout)


def truncate_table(conn):
    log.info("Truncating qld_cadastre_parcels...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE qld_cadastre_parcels CASCADE")
    conn.commit()


def run_ogr2ogr(gdb: str):
    """
    Load QLD_CADASTRE_DCDB parcels into qld_cadastre_parcels using ogr2ogr.

    -append: inserts into existing table (created by migration 001, preserves indexes)
    -sql:    renames and filters source fields to match our schema
    -lco GEOMETRY_NAME=geometry: writes to the 'geometry' column (not 'wkb_geometry')
    -lco FID=id: uses our 'id' SERIAL primary key
    """
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        pg_dsn(),
        gdb,
        "-sql", SELECT_SQL,
        "-nln", "qld_cadastre_parcels",
        "-t_srs", "EPSG:7844",
        "-nlt", "MULTIPOLYGON",
        "-lco", "GEOMETRY_NAME=geometry",
        "-lco", "FID=id",
        "-append",
        "-progress",
    ]

    log.info(f"Loading '{PARCELS_LAYER}' from {gdb}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        log.error("ogr2ogr failed — check the output above for details")
        sys.exit(1)


def rebuild_index(conn):
    log.info("Rebuilding spatial index...")
    with conn.cursor() as cur:
        cur.execute("REINDEX INDEX idx_qld_cadastre_geometry")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Import QLD DCDB .gdb into PostgreSQL")
    parser.add_argument("--gdb", required=True,
                        help="Path to DP_QLD_DCDB_WOS_CUR_GDA2020.gdb directory")
    parser.add_argument("--list-layers", action="store_true",
                        help="List layers and fields in the GDB then exit")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate qld_cadastre_parcels before importing")
    args = parser.parse_args()

    if not Path(args.gdb).exists():
        log.error(f"GDB not found: {args.gdb}")
        sys.exit(1)

    if args.list_layers:
        list_layers(args.gdb)
        sys.exit(0)

    conn = get_connection()
    try:
        if args.truncate:
            truncate_table(conn)

        run_ogr2ogr(args.gdb)
        rebuild_index(conn)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM qld_cadastre_parcels")
            log.info(f"qld_cadastre_parcels: {cur.fetchone()[0]:,} rows")

        log.info("QLD Cadastre import complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
