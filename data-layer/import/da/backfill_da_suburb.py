#!/usr/bin/env python3
"""OBSOLETE — superseded by migration 029 (goldcoast_da_properties).

Suburb resolution now happens per property row in upsert_da_properties()
inside import_goldcoast_da.py during --enrich. The lot_on_plan and lot_plan
columns this script operated on have been dropped from goldcoast_dev_applications.

This file is kept for reference only and will raise an error if run.
"""

raise SystemExit(
    "backfill_da_suburb.py is obsolete. "
    "Suburb is now resolved per-property during --enrich (migration 029)."
)
