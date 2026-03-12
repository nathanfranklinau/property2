#!/usr/bin/env python3
"""
Import all layers from the QLD DCDB (Digital Cadastral Database) File Geodatabase.

Layers imported:
    QLD_CADASTRE_DCDB      → qld_cadastre_parcels   (3.5M MultiPolygon parcels)
    QLD_LOCATION_ADDRESS   → qld_cadastre_address    (2.8M Point addresses)
    QLD_CADASTRE_BUP_LOT   → qld_cadastre_bup_lot   (289K non-spatial BUP lots)
    QLD_CADASTRE_NATBDY    → qld_cadastre_natbdy     (172K MultiLineString natural boundaries)
    QLD_CADASTRE_ROAD      → qld_cadastre_road       (3.7M MultiLineString roads)

Usage:
    python import_qld_cadastre.py --gdb /path/to/DP_QLD_DCDB_WOS_CUR_GDA2020.gdb
    python import_qld_cadastre.py --gdb ... --truncate
    python import_qld_cadastre.py --gdb ... --layers parcels address
    python import_qld_cadastre.py --gdb ... --list-layers

Prerequisites:
    GDAL with OpenFileGDB driver: brew install gdal
    Migration 013 applied (creates new tables + adds columns to qld_cadastre_parcels)

Source:
    https://www.data.qld.gov.au/dataset/queensland-cadastral-data
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


# ─────────────────────────────────────────────
# Layer definitions: GDB layer → DB table config
# ─────────────────────────────────────────────

LAYERS = {
    "parcels": {
        "gdb_layer": "QLD_CADASTRE_DCDB",
        "table": "qld_cadastre_parcels",
        "geom_type": "MULTIPOLYGON",
        "sql": (
            'SELECT '
            '"LOT" AS lot, "PLAN" AS plan, "LOTPLAN" AS lotplan, '
            '"LOT_AREA" AS lot_area, "EXCL_AREA" AS excl_area, '
            '"SEG_NUM" AS seg_num, "PAR_NUM" AS par_num, "SEGPAR" AS segpar, '
            '"PAR_IND" AS par_ind, "LOT_VOLUME" AS lot_volume, '
            '"SURV_IND" AS surv_ind, "TENURE" AS tenure, "PRC" AS prc, '
            '"PARISH" AS parish, "COUNTY" AS county, "LAC" AS lac, '
            '"SHIRE_NAME" AS shire_name, "FEAT_NAME" AS feat_name, '
            '"ALIAS_NAME" AS alias_name, "LOC" AS loc, "LOCALITY" AS locality, '
            '"PARCEL_TYP" AS parcel_typ, "COVER_TYP" AS cover_typ, '
            '"ACC_CODE" AS acc_code, "CA_AREA_SQM" AS ca_area_sqm, '
            '"SMIS_MAP" AS smis_map '
            'FROM "QLD_CADASTRE_DCDB"'
        ),
        "spatial_index": "idx_qld_cadastre_geometry",
    },
    "address": {
        "gdb_layer": "QLD_LOCATION_ADDRESS",
        "table": "qld_cadastre_address",
        "geom_type": "POINT",
        "sql": (
            'SELECT '
            '"LOT" AS lot, "PLAN" AS plan, "LOTPLAN" AS lotplan, '
            '"UNIT_TYPE" AS unit_type, "UNIT_NUMBER" AS unit_number, '
            '"UNIT_SUFFIX" AS unit_suffix, "FLOOR_TYPE" AS floor_type, '
            '"FLOOR_NUMBER" AS floor_number, "FLOOR_SUFFIX" AS floor_suffix, '
            '"PROPERTY_NAME" AS property_name, '
            '"STREET_NO_1" AS street_no_1, "STREET_NO_1_SUFFIX" AS street_no_1_suffix, '
            '"STREET_NO_2" AS street_no_2, "STREET_NO_2_SUFFIX" AS street_no_2_suffix, '
            '"STREET_NUMBER" AS street_number, "STREET_NAME" AS street_name, '
            '"STREET_TYPE" AS street_type, "STREET_SUFFIX" AS street_suffix, '
            '"STREET_FULL" AS street_full, "LOCALITY" AS locality, '
            '"LOCAL_AUTHORITY" AS local_authority, "STATE" AS state, '
            '"ADDRESS" AS address, "ADDRESS_STATUS" AS address_status, '
            '"ADDRESS_STANDARD" AS address_standard, '
            '"LOTPLAN_STATUS" AS lotplan_status, "ADDRESS_PID" AS address_pid, '
            '"GEOCODE_TYPE" AS geocode_type, '
            '"LATITUDE" AS latitude, "LONGITUDE" AS longitude '
            'FROM "QLD_LOCATION_ADDRESS"'
        ),
        "spatial_index": "idx_qld_cadastre_address_geometry",
    },
    "bup_lot": {
        "gdb_layer": "QLD_CADASTRE_BUP_LOT",
        "table": "qld_cadastre_bup_lot",
        "geom_type": None,  # non-spatial
        "sql": (
            'SELECT '
            '"LOTPLAN" AS lotplan, "BUP_LOT" AS bup_lot, '
            '"BUP_PLAN" AS bup_plan, "BUP_LOTPLAN" AS bup_lotplan, '
            '"LOT_AREA_AM" AS lot_area_am '
            'FROM "QLD_CADASTRE_BUP_LOT"'
        ),
        "spatial_index": None,
    },
    "natbdy": {
        "gdb_layer": "QLD_CADASTRE_NATBDY",
        "table": "qld_cadastre_natbdy",
        "geom_type": "MULTILINESTRING",
        "sql": (
            'SELECT '
            '"LINESTYLE" AS linestyle, "SEG_NUM" AS seg_num, "PAR_NUM" AS par_num '
            'FROM "QLD_CADASTRE_NATBDY"'
        ),
        "spatial_index": "idx_qld_cadastre_natbdy_geometry",
    },
    "road": {
        "gdb_layer": "QLD_CADASTRE_ROAD",
        "table": "qld_cadastre_road",
        "geom_type": "MULTILINESTRING",
        "sql": (
            'SELECT '
            '"LINESTYLE" AS linestyle, "SEG_NUM" AS seg_num, "PAR_NUM" AS par_num '
            'FROM "QLD_CADASTRE_ROAD"'
        ),
        "spatial_index": "idx_qld_cadastre_road_geometry",
    },
}

ALL_LAYER_NAMES = list(LAYERS.keys())


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


def truncate_table(conn, table: str):
    log.info(f"Truncating {table}...")
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {table} CASCADE")
    conn.commit()


def import_layer(gdb: str, layer_key: str):
    """Load a single GDB layer into its PostgreSQL table using ogr2ogr."""
    cfg = LAYERS[layer_key]
    log.info(f"Importing {cfg['gdb_layer']} → {cfg['table']}...")

    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        pg_dsn(),
        gdb,
        "-sql", cfg["sql"],
        "-nln", cfg["table"],
        "-lco", "GEOMETRY_NAME=geometry",
        "-lco", "FID=id",
        "-append",
        "-progress",
    ]

    # Spatial layers need SRS + geometry type
    if cfg["geom_type"]:
        cmd.extend(["-t_srs", "EPSG:7844", "-nlt", cfg["geom_type"]])

    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error(f"ogr2ogr failed for {cfg['gdb_layer']}")
        sys.exit(1)

    log.info(f"  {cfg['gdb_layer']} loaded successfully.")


def rebuild_index(conn, index_name: str):
    if not index_name:
        return
    log.info(f"  Rebuilding index {index_name}...")
    with conn.cursor() as cur:
        cur.execute(f"REINDEX INDEX {index_name}")
    conn.commit()


def count_rows(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import QLD DCDB .gdb into PostgreSQL")
    parser.add_argument("--gdb", required=True,
                        help="Path to DP_QLD_DCDB_WOS_CUR_GDA2020.gdb directory")
    parser.add_argument("--list-layers", action="store_true",
                        help="List layers and fields in the GDB then exit")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="Truncate target tables before importing")
    parser.add_argument("--layers", nargs="+", choices=ALL_LAYER_NAMES,
                        default=ALL_LAYER_NAMES,
                        help=f"Which layers to import (default: all). Choices: {ALL_LAYER_NAMES}")
    args = parser.parse_args()

    if not Path(args.gdb).exists():
        log.error(f"GDB not found: {args.gdb}")
        sys.exit(1)

    if args.list_layers:
        list_layers(args.gdb)
        sys.exit(0)

    conn = get_connection()
    try:
        for layer_key in args.layers:
            cfg = LAYERS[layer_key]

            if args.truncate:
                truncate_table(conn, cfg["table"])

            import_layer(args.gdb, layer_key)
            rebuild_index(conn, cfg["spatial_index"])

            rows = count_rows(conn, cfg["table"])
            log.info(f"  {cfg['table']}: {rows:,} rows")

        log.info("QLD Cadastre import complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
