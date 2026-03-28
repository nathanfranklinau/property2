#!/usr/bin/env python3
"""Import Western Downs Regional Council development applications from Development.i.

Thin wrapper around the generic Development.i importer.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_westerndowns_da.py                    # delta 30 days
    python import_westerndowns_da.py --full             # full import
    python import_westerndowns_da.py --enrich           # enrich unenriched
    python import_westerndowns_da.py --enrich --workers 4
    python import_westerndowns_da.py --monitor          # re-check active
    python import_westerndowns_da.py --app APP_NUMBER   # enrich one app
"""

from import_developmenti_da import COUNCILS, run

if __name__ == "__main__":
    run(COUNCILS["westerndowns"])
