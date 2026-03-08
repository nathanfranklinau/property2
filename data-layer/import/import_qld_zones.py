#!/usr/bin/env python3
"""
Import QLD Planning Scheme Zones into PostgreSQL.

Uses ogr2ogr (GDAL) to load from GeoPackage, Shapefile, or GDB.

Usage:
    python import_qld_zones.py --src /path/to/QLD_PLAN_ZONES.gpkg
    python import_qld_zones.py --src /path/to/QLD_PLAN_ZONES.gpkg --truncate
    python import_qld_zones.py --src /path/to/QLD_PLAN_ZONES.gpkg --list-layers
    python import_qld_zones.py --src ... --layer-name <name>

Source:
    QLD Spatial Catalogue — "Planning Scheme Zones"
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

# Default layer name — use --list-layers to check actual layer names in your download.
DEFAULT_LAYER = "QLD_PLAN_ZONE"


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
    log.info("Truncating qld_planning_zones...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE qld_planning_zones CASCADE")
    conn.commit()


def run_ogr2ogr(src: str, layer_name: str):
    """
    Load planning zone polygons into qld_planning_zones using ogr2ogr.

    Field names vary by dataset version. Common patterns:
      - ZONE_CODE / Zone_Code → zone_code
      - ZONE_NAME / Zone_Name → zone_name
      - PS_NAME / Planning_Scheme → planning_scheme
      - LGA / LGA_NAME → lga
    """
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        pg_dsn(),
        src,
        layer_name,
        "-nln", "qld_planning_zones",
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
    After ogr2ogr loads raw data, map source field names to our schema.
    Different dataset versions use different naming conventions.
    """
    log.info("Running post-import field cleanup...")
    with conn.cursor() as cur:
        # Try to populate zone_code from common source field patterns
        for src_field in ["zone_code", "zonecode", "zon_code"]:
            try:
                cur.execute(f"""
                    UPDATE qld_planning_zones
                    SET zone_code = {src_field}
                    FROM (SELECT id, {src_field} FROM qld_planning_zones WHERE {src_field} IS NOT NULL) src
                    WHERE qld_planning_zones.id = src.id AND qld_planning_zones.zone_code IS NULL
                """)
                if cur.rowcount > 0:
                    log.info(f"  Populated zone_code from '{src_field}' ({cur.rowcount} rows)")
                    break
            except Exception:
                conn.rollback()
                continue

        # Try to populate zone_name
        for src_field in ["zone_name", "zonename", "zon_name"]:
            try:
                cur.execute(f"""
                    UPDATE qld_planning_zones
                    SET zone_name = {src_field}
                    FROM (SELECT id, {src_field} FROM qld_planning_zones WHERE {src_field} IS NOT NULL) src
                    WHERE qld_planning_zones.id = src.id AND qld_planning_zones.zone_name IS NULL
                """)
                if cur.rowcount > 0:
                    log.info(f"  Populated zone_name from '{src_field}' ({cur.rowcount} rows)")
                    break
            except Exception:
                conn.rollback()
                continue

        # Try to populate planning_scheme
        for src_field in ["planning_scheme", "ps_name", "scheme_name"]:
            try:
                cur.execute(f"""
                    UPDATE qld_planning_zones
                    SET planning_scheme = {src_field}
                    FROM (SELECT id, {src_field} FROM qld_planning_zones WHERE {src_field} IS NOT NULL) src
                    WHERE qld_planning_zones.id = src.id AND qld_planning_zones.planning_scheme IS NULL
                """)
                if cur.rowcount > 0:
                    log.info(f"  Populated planning_scheme from '{src_field}' ({cur.rowcount} rows)")
                    break
            except Exception:
                conn.rollback()
                continue

        conn.commit()


def rebuild_index(conn):
    log.info("Rebuilding spatial index...")
    with conn.cursor() as cur:
        cur.execute("REINDEX INDEX idx_qld_zones_geometry")
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Import QLD Planning Zones into PostgreSQL")
    parser.add_argument("--src", required=True,
                        help="Path to source file (.gpkg, .shp, or .gdb)")
    parser.add_argument("--layer-name", default=DEFAULT_LAYER,
                        help=f"Layer name in source file (default: {DEFAULT_LAYER})")
    parser.add_argument("--list-layers", action="store_true",
                        help="List layers and fields in the source then exit")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate qld_planning_zones before importing")
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
        post_import_cleanup(conn)
        rebuild_index(conn)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM qld_planning_zones")
            log.info(f"qld_planning_zones: {cur.fetchone()[0]:,} rows")

        log.info("QLD Planning Zones import complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
