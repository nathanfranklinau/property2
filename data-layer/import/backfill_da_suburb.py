#!/usr/bin/env python3
"""One-time backfill: populate suburb on goldcoast_dev_applications from qld_cadastre_address.

For each DA that has a lot_plan value (derived from lot_on_plan), looks up the
corresponding locality in qld_cadastre_address and writes it to the suburb column.

Usage:
    cd data-layer
    source venv/bin/activate
    python import/backfill_da_suburb.py
"""

import logging
import os
import re
import sys

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from import_goldcoast_da import get_connection

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("backfill_da_suburb")

BATCH_SIZE = 500


def derive_lot_plan(lot_on_plan: str | None) -> str | None:
    """Mirror the lot_plan generated column: strip 'Lot ' prefix + all spaces."""
    if not lot_on_plan:
        return None
    return re.sub(r"(?i)^\s*lot\s+", "", lot_on_plan).replace(" ", "") or None


def main():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT application_number, lot_on_plan "
        "FROM goldcoast_dev_applications "
        "WHERE lot_on_plan IS NOT NULL"
    )
    rows = cur.fetchall()
    log.info(f"Found {len(rows)} applications with lot_on_plan")

    # Bulk-fetch all relevant cadastre localities in one query
    lot_plans = list({derive_lot_plan(r[1]) for r in rows if derive_lot_plan(r[1])})
    log.info(f"Looking up {len(lot_plans)} distinct lot/plan values in cadastre")

    cur.execute(
        "SELECT lotplan, locality FROM qld_cadastre_address WHERE lotplan = ANY(%s)",
        (lot_plans,),
    )
    cadastre_map = {r[0]: r[1] for r in cur.fetchall()}
    log.info(f"Matched {len(cadastre_map)} lot/plan values to a locality")

    updates = []
    for app_num, lot_on_plan in rows:
        lot_plan = derive_lot_plan(lot_on_plan)
        locality = cadastre_map.get(lot_plan)
        if locality:
            updates.append((locality, app_num))

    log.info(f"Updating suburb on {len(updates)} applications")

    sql = "UPDATE goldcoast_dev_applications SET suburb = %s WHERE application_number = %s"
    total = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        cur.executemany(sql, batch)
        conn.commit()
        total += len(batch)
        log.info(f"  Updated {total}/{len(updates)}")

    log.info("Backfill complete")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
