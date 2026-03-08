#!/usr/bin/env python3
"""
Import Geoscape Administrative Boundaries into PostgreSQL.

Loads all states for: LGA, Localities, State Boundaries, and Wards.

Usage:
    python import/import_admin_boundaries.py --src /path/to/FEB26_AdminBounds_GDA_2020_SHP
    python import/import_admin_boundaries.py --src /path/to/... --truncate

Source:
    Geoscape Administrative Boundaries (GDA2020)
    https://data.gov.au/data/dataset/geoscape-administrative-boundaries

Prerequisites:
    GDAL (brew install gdal)
    pip install psycopg2-binary python-dotenv
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


# ── Configuration ─────────────────────────────────────────────────────────────

# Maps table name → glob pattern relative to the dataset root directory.
# Each glob may match multiple per-state shapefiles that are appended together.
LAYERS = [
    {
        "table": "gnaf_admin_lga",
        "glob": "LocalGovernmentAreas_*/**/*_lga.shp",
        "description": "Local Government Areas",
    },
    {
        "table": "gnaf_admin_localities",
        "glob": "Localities_*/**/*_localities.shp",
        "description": "Localities (suburbs/towns)",
    },
    {
        "table": "gnaf_admin_state_boundaries",
        "glob": "StateBoundaries_*/**/*_STATE_POLYGON_shp.shp",
        "description": "State Boundaries",
    },
    {
        "table": "gnaf_admin_wards",
        "glob": "Wards_*/**/*_wards.shp",
        "description": "Council Wards",
    },
]


# ── DB helpers ────────────────────────────────────────────────────────────────

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


# ── Import logic ──────────────────────────────────────────────────────────────

def find_shapefiles(src: Path, pattern: str) -> list[Path]:
    """Return all shapefiles matching the glob pattern under src, sorted."""
    return sorted(src.glob(pattern))


def truncate_tables(conn):
    tables = [layer["table"] for layer in LAYERS]
    log.info(f"Truncating: {', '.join(tables)}")
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"TRUNCATE {table}")
    conn.commit()


def load_shapefile(shp: Path, table: str):
    """Load a single shapefile into the target table using ogr2ogr."""
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        pg_dsn(),
        str(shp),
        "-nln", table,
        "-append",
        "-t_srs", "EPSG:7844",
        "-nlt", "PROMOTE_TO_MULTI",   # handles Polygon → MultiPolygon
        "-lco", "GEOMETRY_NAME=geom", # no-op on append but harmless
        "-progress",
    ]
    log.info(f"  Loading {shp.name} → {table}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error(f"ogr2ogr failed on {shp}")
        sys.exit(1)


def import_layer(src: Path, layer: dict):
    shapefiles = find_shapefiles(src, layer["glob"])
    if not shapefiles:
        log.warning(f"No shapefiles found for {layer['description']} (pattern: {layer['glob']})")
        return 0

    log.info(f"── {layer['description']} ({len(shapefiles)} files) → {layer['table']}")
    for shp in shapefiles:
        load_shapefile(shp, layer["table"])
    return len(shapefiles)


def row_counts(conn) -> dict[str, int]:
    counts = {}
    with conn.cursor() as cur:
        for layer in LAYERS:
            table = layer["table"]
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = -1
    return counts


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import Geoscape Administrative Boundaries into PostgreSQL"
    )
    parser.add_argument(
        "--src", required=True,
        help="Path to the Geoscape AdminBounds root directory (e.g. FEB26_AdminBounds_GDA_2020_SHP)",
    )
    parser.add_argument(
        "--truncate", action="store_true", default=False,
        help="Truncate all admin boundary tables before importing",
    )
    args = parser.parse_args()

    src = Path(args.src)
    if not src.is_dir():
        log.error(f"Source directory not found: {src}")
        sys.exit(1)

    conn = get_connection()
    try:
        if args.truncate:
            truncate_tables(conn)

        total_files = 0
        for layer in LAYERS:
            total_files += import_layer(src, layer)

        counts = row_counts(conn)
        log.info("── Row counts:")
        for table, n in counts.items():
            log.info(f"   {table}: {n:,}")

        log.info(f"Import complete ({total_files} shapefiles loaded).")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
