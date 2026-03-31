#!/usr/bin/env python3
"""Import Sunshine Coast Regional Council development applications from Development.i.

Wrapper around the generic Development.i importer with Sunshine Coast-specific config.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_sunshinecoast_da.py                    # delta 30 days
    python import_sunshinecoast_da.py --full             # full import
    python import_sunshinecoast_da.py --enrich           # enrich unenriched
    python import_sunshinecoast_da.py --enrich --workers 4
    python import_sunshinecoast_da.py --monitor          # re-check active
    python import_sunshinecoast_da.py --app APP_NUMBER   # enrich one app
"""

from import_developmenti_da import (
    GROUPS_DA_BA_PLUMB,
    CouncilConfig,
    run,
    DEFAULT_CSV_FIELD_MAP,
    DEFAULT_DETAIL_TEXT_FIELDS,
    DEFAULT_DETAIL_DATE_FIELDS,
)

CONFIG: CouncilConfig = {
    "name": "Sunshine Coast",
    "slug": "sunshinecoast",
    "base_url": "https://developmenti.sunshinecoast.qld.gov.au",
    "lga_pid": "lgaa9ec4359b5d6",
    "full_start_date": "2020-01-01",
    "groups": GROUPS_DA_BA_PLUMB,
    "filter_panel_selector": "#search-filters",
    "filter_panel_needs_show": True,
    "date_input_selector": "#dateRangeInput",
    "group_select_id": "filter-application-group",
    # Sunshine Coast uses ?ApplicationId= (capital A)
    "detail_param": "ApplicationId",
    "has_detail_pages": True,
    "description_addr_at_end": False,
    "ignore_https_errors": False,
    "use_filter_direct": False,
    "csv_field_map": DEFAULT_CSV_FIELD_MAP,
    "detail_text_fields": DEFAULT_DETAIL_TEXT_FIELDS,
    "detail_date_fields": DEFAULT_DETAIL_DATE_FIELDS,
}

if __name__ == "__main__":
    run(CONFIG)
