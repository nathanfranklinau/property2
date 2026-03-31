#!/usr/bin/env python3
"""Import Toowoomba Regional Council development applications from Development.i.

Wrapper around the generic Development.i importer with Toowoomba-specific config.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_toowoomba_da.py                    # delta 30 days
    python import_toowoomba_da.py --full             # full import
    python import_toowoomba_da.py --enrich           # enrich unenriched
    python import_toowoomba_da.py --enrich --workers 4
    python import_toowoomba_da.py --monitor          # re-check active
    python import_toowoomba_da.py --app APP_NUMBER   # enrich one app
"""

from import_developmenti_da import (
    GROUPS_DA_ONLY,
    CouncilConfig,
    run,
    DEFAULT_CSV_FIELD_MAP,
    DEFAULT_DETAIL_TEXT_FIELDS,
    DEFAULT_DETAIL_DATE_FIELDS,
)

CONFIG: CouncilConfig = {
    "name": "Toowoomba",
    "slug": "toowoomba",
    "base_url": "https://developmenti.tr.qld.gov.au",
    "lga_pid": "lga59db913dcc12",
    "full_start_date": "1998-01-01",
    "groups": GROUPS_DA_ONLY,
    "filter_panel_selector": "#search-filters",
    "filter_panel_needs_show": True,
    "date_input_selector": "#dateRangeInput",
    "group_select_id": "filter-application-group",
    "detail_param": "id",
    "has_detail_pages": True,
    # Toowoomba description format: "Proposal - ADDRESS SUBURB QLD POSTCODE"
    # Address is at the END, not the start (opposite to Brisbane).
    "description_addr_at_end": True,
    "ignore_https_errors": False,
    "use_filter_direct": False,
    "csv_field_map": DEFAULT_CSV_FIELD_MAP,
    "detail_text_fields": DEFAULT_DETAIL_TEXT_FIELDS,
    "detail_date_fields": DEFAULT_DETAIL_DATE_FIELDS,
}

if __name__ == "__main__":
    run(CONFIG)
