#!/usr/bin/env python3
"""
Import QLD Local Government Area boundaries into PostgreSQL.

Uses ogr2ogr (GDAL) to load a GeoPackage or Shapefile from QLD Spatial Catalogue.

Usage:
    python import_qld_lga.py --src /path/to/QLD_LGA.gpkg
    python import_qld_lga.py --src /path/to/QLD_LGA.gpkg --truncate
    python import_qld_lga.py --src /path/to/QLD_LGA.gpkg --list-layers
    python import_qld_lga.py --src /path/to/QLD_LGA.shp --layer-name <name>

Source:
    QLD Spatial Catalogue — "Local Government Areas - Queensland"
    https://qldspatial.information.qld.gov.au/catalogue/

Prerequisites:
    GDAL with appropriate driver (brew install gdal)
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

# Default layer name — may vary depending on the download format.
# Use --list-layers to check, then override with --layer-name if different.
DEFAULT_LAYER = "QLD_LGA"


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


def list_layers(src: str):
    result = subprocess.run(["ogrinfo", "-al", "-so", src], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)


def truncate_table(conn):
    log.info("Truncating qld_lga_boundaries...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE qld_lga_boundaries CASCADE")
    conn.commit()


def run_ogr2ogr(src: str, layer_name: str):
    """
    Load LGA boundaries into qld_lga_boundaries using ogr2ogr.

    The SQL selects and renames fields to match our schema.
    Field names vary by dataset — common patterns:
      - ABBREV_NAME / LGA_NAME_2021 / NAME → lga_name
      - LGA_CODE_2021 / CODE → lga_code

    Adjust the SELECT SQL below after inspecting your download with --list-layers.
    """
    # Broad SQL that works for common QLD LGA dataset field names.
    # The source typically has: ABBREV_NAME, LGA_CODE21 or similar.
    # We use a permissive approach — select all and rely on -nln mapping.
    select_sql = (
        f'SELECT *, '
        f'COALESCE("ABBREV_NAME", "LGA_NAME", "NAME", "lga_name") AS lga_name_mapped, '
        f'COALESCE("LGA_CODE", "LGA_CODE21", "CODE", "lga_code") AS lga_code_mapped '
        f'FROM "{layer_name}"'
    )

    # Simpler approach: load all fields, then clean up. ogr2ogr will map geometry automatically.
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        pg_dsn(),
        src,
        layer_name,
        "-nln", "qld_lga_boundaries",
        "-t_srs", "EPSG:7844",
        "-nlt", "MULTIPOLYGON",
        "-lco", "GEOMETRY_NAME=geometry",
        "-lco", "FID=id",
        "-append",
        "-progress",
    ]

    log.info(f"Loading layer '{layer_name}' from {src}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        log.error("ogr2ogr failed — check output above. Try --list-layers to verify layer/field names.")
        sys.exit(1)


def post_import_cleanup(conn):
    """
    After ogr2ogr loads raw data, ensure lga_name and lga_code are populated.
    Different source datasets use different field names; this handles common patterns.
    """
    log.info("Running post-import field cleanup...")
    with conn.cursor() as cur:
        # Try common field name patterns to populate lga_name if it's null
        for src_field in ["abbrev_name", "lga_name_2021", "name"]:
            cur.execute(f"""
                UPDATE qld_lga_boundaries
                SET lga_name = {src_field}
                FROM (SELECT id, {src_field} FROM qld_lga_boundaries WHERE {src_field} IS NOT NULL) src
                WHERE qld_lga_boundaries.id = src.id AND qld_lga_boundaries.lga_name IS NULL
            """)
            if cur.rowcount > 0:
                log.info(f"  Populated lga_name from '{src_field}' ({cur.rowcount} rows)")
                break
        conn.commit()


def rebuild_index(conn):
    log.info("Rebuilding spatial index...")
    with conn.cursor() as cur:
        cur.execute("REINDEX INDEX idx_qld_lga_geometry")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Import QLD LGA boundaries into PostgreSQL")
    parser.add_argument("--src", required=True,
                        help="Path to source file (.gpkg, .shp, or .gdb)")
    parser.add_argument("--layer-name", default=DEFAULT_LAYER,
                        help=f"Layer name in source file (default: {DEFAULT_LAYER})")
    parser.add_argument("--list-layers", action="store_true",
                        help="List layers and fields in the source then exit")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate qld_lga_boundaries before importing")
    args = parser.parse_args()

    if not Path(args.src).exists():
        log.error(f"Source file not found: {args.src}")
        sys.exit(1)

    if args.list_layers:
        list_layers(args.src)
        sys.exit(0)

    conn = get_connection()
    try:
        if args.truncate:
            truncate_table(conn)

        run_ogr2ogr(args.src, args.layer_name)
        rebuild_index(conn)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM qld_lga_boundaries")
            log.info(f"qld_lga_boundaries: {cur.fetchone()[0]:,} rows")

        log.info("QLD LGA import complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
