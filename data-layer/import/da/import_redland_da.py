#!/usr/bin/env python3
"""Import Redland City Council development applications from Development.i.

Wrapper around the generic Development.i importer with Redland-specific config.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_redland_da.py                    # delta 30 days
    python import_redland_da.py --full             # full import
    python import_redland_da.py --enrich           # enrich unenriched
    python import_redland_da.py --enrich --workers 4
    python import_redland_da.py --monitor          # re-check active
    python import_redland_da.py --app APP_NUMBER   # enrich one app
"""

from import_developmenti_da import GROUPS_DA_BA_PLUMB, CouncilConfig, run

CONFIG: CouncilConfig = {
    "name": "Redland",
    "slug": "redland",
    "base_url": "https://developmenti.redland.qld.gov.au",
    "lga_pid": "lga42379c2c72f3",
    "full_start_date": "2020-01-01",
    "groups": GROUPS_DA_BA_PLUMB,
    # Redland uses div#filter-container, which is not hidden by default
    "filter_panel_selector": "#filter-container",
    "filter_panel_needs_show": False,
    "date_input_selector": "input[name='daterange']",
    "group_select_id": "filter-application-group",
    "detail_param": "applicationNumber",
    "has_detail_pages": True,
    "description_addr_at_end": False,
    "ignore_https_errors": False,
    "use_filter_direct": False,
}

if __name__ == "__main__":
    run(CONFIG)
