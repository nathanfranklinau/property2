#!/usr/bin/env python3
"""One-time backfill: parse DA descriptions into structured category columns.

Reads all rows from development_applications, runs parse_description()
on each, and batch-updates the parsed fields.

Usage:
    cd data-layer
    source venv/bin/activate
    python import/backfill_da_categories.py
"""

import logging
import os
import sys

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Import parse_description from the DA import script
sys.path.insert(0, os.path.dirname(__file__))
from da_common import parse_description, get_connection

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("backfill_da_categories")

BATCH_SIZE = 500


def main():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, description, application_type "
        "FROM development_applications"
    )
    rows = cur.fetchall()
    log.info(f"Processing {len(rows)} applications")

    updates = []
    for row_id, description, app_type in rows:
        parsed = parse_description(description, app_type)
        updates.append((
            parsed["development_category"],
            parsed["dwelling_type"],
            parsed["unit_count"],
            parsed["lot_split_from"],
            parsed["lot_split_to"],
            parsed["assessment_level"],
            row_id,
        ))

    # Batch update
    sql = """
        UPDATE development_applications SET
            development_category = %s,
            dwelling_type = %s,
            unit_count = %s,
            lot_split_from = %s,
            lot_split_to = %s,
            assessment_level = %s
        WHERE id = %s
    """

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
