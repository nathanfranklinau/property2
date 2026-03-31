#!/usr/bin/env python3
"""Import Western Downs Regional Council development applications from Development.i.

Wrapper around the generic Development.i importer with Western Downs-specific config.
See import_developmenti_da.py for full documentation and usage.

Usage:
    python import_westerndowns_da.py                    # delta 30 days
    python import_westerndowns_da.py --full             # full import
    python import_westerndowns_da.py --enrich           # enrich unenriched
    python import_westerndowns_da.py --enrich --workers 4
    python import_westerndowns_da.py --monitor          # re-check active
    python import_westerndowns_da.py --app APP_NUMBER   # enrich one app
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
    "name": "Western Downs",
    "slug": "westerndowns",
    "base_url": "https://developmenti.wdrc.qld.gov.au",
    "lga_pid": "lga1be86b7b4de2",
    "full_start_date": "2017-01-01",
    "groups": GROUPS_DA_ONLY,
    # Filter panel is visible by default on WDRC — no force-show needed
    "filter_panel_selector": "#search-filters",
    "filter_panel_needs_show": False,
    "date_input_selector": "#dateRangeInput",
    "group_select_id": "filter-application-group",
    "detail_param": "id",
    # WDRC uses AJAX modals only — no standalone ApplicationDetailsView.
    # Enrichment falls back to the /Geo/GetApplicationById JSON API.
    "has_detail_pages": False,
    "description_addr_at_end": False,
    # SSL certificate is expired — suppress cert validation errors.
    "ignore_https_errors": True,
    "use_filter_direct": False,
    "csv_field_map": DEFAULT_CSV_FIELD_MAP,
    "detail_text_fields": DEFAULT_DETAIL_TEXT_FIELDS,
    "detail_date_fields": DEFAULT_DETAIL_DATE_FIELDS,
}

if __name__ == "__main__":
    run(CONFIG)
