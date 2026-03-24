"""Fetch all DA location_address values from the DB and write to CSV files.

Run from data-layer/: ../venv/bin/python addr_eval/fetch_data.py

Produces:
  addr_eval/data/gc_addresses.csv   — goldcoast_da_properties
  addr_eval/data/bris_addresses.csv — brisbane_da_properties
"""

import csv
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch(conn: psycopg2.extensions.connection, query: str) -> list[tuple]:
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    return rows


def write_csv(path: str, headers: list[str], rows: list[tuple]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {path}")


def main() -> None:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "subdivide"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )

    # Gold Coast — all distinct location_address values plus ground truth parsed fields
    # Note: goldcoast_da_properties has no postcode column; suburb=portal_suburb
    gc_rows = fetch(conn, """
        SELECT DISTINCT ON (location_address)
            location_address,
            street_number,
            street_name,
            street_type,
            unit_type,
            unit_number,
            unit_suffix,
            portal_suburb AS suburb,
            NULL AS postcode
        FROM goldcoast_da_properties
        WHERE location_address IS NOT NULL
        ORDER BY location_address
    """)
    write_csv(
        os.path.join(DATA_DIR, "gc_addresses.csv"),
        ["location_address", "street_number", "street_name", "street_type",
         "unit_type", "unit_number", "unit_suffix", "suburb", "postcode"],
        gc_rows,
    )

    # Brisbane — all rows
    bris_rows = fetch(conn, """
        SELECT DISTINCT ON (location_address)
            location_address,
            street_number,
            street_name,
            street_type,
            unit_type,
            unit_number,
            unit_suffix,
            NULL as suburb,
            NULL as postcode
        FROM brisbane_da_properties
        WHERE location_address IS NOT NULL
        ORDER BY location_address
    """)
    write_csv(
        os.path.join(DATA_DIR, "bris_addresses.csv"),
        ["location_address", "street_number", "street_name", "street_type",
         "unit_type", "unit_number", "unit_suffix", "suburb", "postcode"],
        bris_rows,
    )

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
