#!/usr/bin/env python3
"""Import Ipswich City Council development applications from Development.i.

Wrapper around the generic Development.i importer with Ipswich-specific config.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_ipswich_da.py                    # delta 30 days
    python import_ipswich_da.py --full             # full import
    python import_ipswich_da.py --enrich           # enrich unenriched
    python import_ipswich_da.py --enrich --workers 4
    python import_ipswich_da.py --monitor          # re-check active
    python import_ipswich_da.py --app APP_NUMBER   # enrich one app
"""

from import_developmenti_da import GROUPS_DA_ONLY, CouncilConfig, run

CONFIG: CouncilConfig = {
    "name": "Ipswich",
    "slug": "ipswich",
    "base_url": "https://developmenti.ipswich.qld.gov.au",
    "lga_pid": "lgafd22606d6b20",
    "full_start_date": "2018-01-01",
    "groups": GROUPS_DA_ONLY,
    "filter_panel_selector": "#search-filters",
    "filter_panel_needs_show": True,
    "date_input_selector": "#dateRangeInput",
    "group_select_id": "filter-application-group",
    # Detail page hangs on direct URL — use FilterDirect flow instead
    "detail_param": "id",
    "has_detail_pages": True,
    "description_addr_at_end": False,
    "ignore_https_errors": False,
    "use_filter_direct": True,
}

if __name__ == "__main__":
    run(CONFIG)
