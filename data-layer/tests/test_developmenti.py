"""Tests for the generic Development.i import script.

Tests all pure functions: CSV parsing, record mapping, address extraction,
date parsing, URL helpers, and council configuration validation.
No database or browser required.
"""

import pytest
from datetime import date

from import_developmenti_da import (
    COUNCILS,
    STAGE_COLUMN_MAP,
    CouncilConfig,
    _extract_description_address,
    _parse_rendered_date,
    parse_csv,
    map_csv_record,
    search_url,
    detail_url,
    property_url,
    build_parser,
    _RE_DESC_ADDR_END,
)


# ── Council configuration validation ─────────────────────────────────────────

class TestCouncilConfigs:
    """Verify every council config has valid structure and values."""

    EXPECTED_COUNCILS = {"ipswich", "redland", "sunshinecoast", "toowoomba", "westerndowns"}

    def test_all_expected_councils_present(self):
        assert set(COUNCILS.keys()) == self.EXPECTED_COUNCILS

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_config_has_required_keys(self, slug: str):
        cfg = COUNCILS[slug]
        required_keys = [
            "name", "slug", "base_url", "parent_table", "child_table",
            "full_start_date", "groups", "filter_panel_selector",
            "filter_panel_needs_show", "date_input_selector", "group_select_id",
            "detail_param", "has_detail_pages", "description_addr_at_end",
            "ignore_https_errors",
        ]
        for key in required_keys:
            assert key in cfg, f"Missing key '{key}' in {slug} config"

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_config_slug_matches_key(self, slug: str):
        assert COUNCILS[slug]["slug"] == slug

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_base_url_is_https(self, slug: str):
        url = COUNCILS[slug]["base_url"]
        assert url.startswith("https://"), f"{slug} base_url should be HTTPS: {url}"

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_base_url_has_no_trailing_slash(self, slug: str):
        assert not COUNCILS[slug]["base_url"].endswith("/")

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_full_start_date_is_valid_iso(self, slug: str):
        d = date.fromisoformat(COUNCILS[slug]["full_start_date"])
        assert d.year >= 1995
        assert d <= date.today()

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_groups_have_development(self, slug: str):
        groups = COUNCILS[slug]["groups"]
        assert "development" in groups
        assert groups["development"]["include_da"] is True

    def test_ipswich_development_only(self):
        """Ipswich portal only exposes the Development group."""
        assert list(COUNCILS["ipswich"]["groups"].keys()) == ["development"]

    def test_toowoomba_development_only(self):
        """Toowoomba portal only exposes the Development group."""
        assert list(COUNCILS["toowoomba"]["groups"].keys()) == ["development"]

    def test_westerndowns_development_only(self):
        """Western Downs portal only exposes the Development group."""
        assert list(COUNCILS["westerndowns"]["groups"].keys()) == ["development"]

    def test_redland_has_three_groups(self):
        """Redland has Development, Building, and Plumbing."""
        groups = set(COUNCILS["redland"]["groups"].keys())
        assert groups == {"development", "building", "plumbing"}

    def test_sunshinecoast_has_three_groups(self):
        """Sunshine Coast has Development, Building, and Plumbing."""
        groups = set(COUNCILS["sunshinecoast"]["groups"].keys())
        assert groups == {"development", "building", "plumbing"}

    def test_redland_uses_filter_container(self):
        """Redland uses div#filter-container, not ul#search-filters."""
        assert COUNCILS["redland"]["filter_panel_selector"] == "#filter-container"

    def test_redland_does_not_need_force_show(self):
        """Redland's filter container is visible by default."""
        assert COUNCILS["redland"]["filter_panel_needs_show"] is False

    def test_westerndowns_does_not_need_force_show(self):
        """Western Downs filter panel is visible by default."""
        assert COUNCILS["westerndowns"]["filter_panel_needs_show"] is False

    def test_panels_that_need_force_show(self):
        """Ipswich, Sunshine Coast, Toowoomba hide filter panel by default."""
        for slug in ("ipswich", "sunshinecoast", "toowoomba"):
            assert COUNCILS[slug]["filter_panel_needs_show"] is True, f"{slug} should need force-show"

    def test_redland_uses_name_daterange(self):
        """Redland uses input[name='daterange'], not #dateRangeInput."""
        assert COUNCILS["redland"]["date_input_selector"] == "input[name='daterange']"

    def test_westerndowns_no_detail_pages(self):
        """Western Downs uses AJAX modals — no standalone detail pages."""
        assert COUNCILS["westerndowns"]["has_detail_pages"] is False

    def test_all_others_have_detail_pages(self):
        for slug in ("ipswich", "redland", "sunshinecoast", "toowoomba"):
            assert COUNCILS[slug]["has_detail_pages"] is True, f"{slug} should have detail pages"

    def test_redland_detail_param_is_applicationNumber(self):
        assert COUNCILS["redland"]["detail_param"] == "applicationNumber"

    def test_sunshinecoast_detail_param_is_ApplicationId(self):
        """Sunshine Coast uses capital-A ApplicationId."""
        assert COUNCILS["sunshinecoast"]["detail_param"] == "ApplicationId"

    def test_ipswich_and_toowoomba_detail_param_is_id(self):
        """Ipswich and Toowoomba use 'id' as the detail page param."""
        for slug in ("ipswich", "toowoomba"):
            assert COUNCILS[slug]["detail_param"] == "id", f"{slug} should use 'id'"

    def test_toowoomba_description_addr_at_end(self):
        """Toowoomba embeds address at the end of description."""
        assert COUNCILS["toowoomba"]["description_addr_at_end"] is True

    def test_all_others_description_addr_at_start(self):
        for slug in ("ipswich", "redland", "sunshinecoast", "westerndowns"):
            assert COUNCILS[slug]["description_addr_at_end"] is False, (
                f"{slug} should have addr at start"
            )

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_parent_table_matches_convention(self, slug: str):
        table = COUNCILS[slug]["parent_table"]
        assert table.endswith("_dev_applications")

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_child_table_matches_convention(self, slug: str):
        table = COUNCILS[slug]["child_table"]
        assert table.endswith("_da_properties")

    @pytest.mark.parametrize("slug", EXPECTED_COUNCILS)
    def test_tables_share_council_prefix(self, slug: str):
        cfg = COUNCILS[slug]
        parent_prefix = cfg["parent_table"].replace("_dev_applications", "")
        child_prefix = cfg["child_table"].replace("_da_properties", "")
        assert parent_prefix == child_prefix


# ── URL helpers ──────────────────────────────────────────────────────────────

class TestUrlHelpers:
    def test_search_url(self):
        cfg = COUNCILS["ipswich"]
        assert search_url(cfg) == "https://developmenti.ipswich.qld.gov.au/Home/MapSearch"

    def test_detail_url(self):
        cfg = COUNCILS["redland"]
        assert detail_url(cfg) == "https://developmenti.redland.qld.gov.au/Home/ApplicationDetailsView"

    def test_property_url(self):
        cfg = COUNCILS["toowoomba"]
        assert property_url(cfg) == "https://developmenti.tr.qld.gov.au/Home/PropertyDetailsView"

    @pytest.mark.parametrize("slug", COUNCILS.keys())
    def test_all_urls_well_formed(self, slug: str):
        cfg = COUNCILS[slug]
        for fn in (search_url, detail_url, property_url):
            url = fn(cfg)
            assert url.startswith("https://")
            assert "/Home/" in url


# ── Address extraction from description ──────────────────────────────────────

class TestExtractDescriptionAddress:
    def test_standard_format(self):
        desc = "123 Smith Street IPSWICH QLD 4305 - Material Change of Use - John Smith - 01/01/2025"
        assert _extract_description_address(desc) == "123 Smith Street IPSWICH QLD 4305"

    def test_five_digit_postcode(self):
        desc = "45 Long Road DALBY QLD 43050 - MCU - Applicant - date"
        assert _extract_description_address(desc) == "45 Long Road DALBY QLD 43050"

    def test_hyphenated_street_number(self):
        desc = "1-3 Main Road REDLAND BAY QLD 4165 - ROL - Builder Inc - 15/03/2025"
        assert _extract_description_address(desc) == "1-3 Main Road REDLAND BAY QLD 4165"

    def test_unit_address(self):
        desc = "Unit 5/42 Beach Avenue CALOUNDRA QLD 4551 - Building Works - Owner - date"
        assert _extract_description_address(desc) == "Unit 5/42 Beach Avenue CALOUNDRA QLD 4551"

    def test_no_qld_sentinel_returns_none(self):
        assert _extract_description_address("Some random description") is None

    def test_empty_string_returns_none(self):
        assert _extract_description_address("") is None

    def test_lowercase_qld(self):
        desc = "10 Test St SOMEWHERE qld 4000 - App - Person - date"
        assert _extract_description_address(desc) == "10 Test St SOMEWHERE qld 4000"

    def test_multi_word_suburb(self):
        desc = "7 Ocean View Drive MOUNT LOFTY QLD 4350 - MCU - Dev Corp - 01/02/2026"
        assert _extract_description_address(desc) == "7 Ocean View Drive MOUNT LOFTY QLD 4350"


# ── Date parsing ─────────────────────────────────────────────────────────────

class TestParseRenderedDate:
    def test_standard_dd_mm_yyyy(self):
        assert _parse_rendered_date("15/03/2025") == date(2025, 3, 15)

    def test_single_digit_day_and_month(self):
        assert _parse_rendered_date("1/2/2025") == date(2025, 2, 1)

    def test_leading_trailing_whitespace(self):
        assert _parse_rendered_date("  15/03/2025  ") == date(2025, 3, 15)

    def test_empty_string_returns_none(self):
        assert _parse_rendered_date("") is None

    def test_none_returns_none(self):
        assert _parse_rendered_date(None) is None

    def test_whitespace_only_returns_none(self):
        assert _parse_rendered_date("   ") is None

    def test_invalid_date_returns_none(self):
        assert _parse_rendered_date("not a date") is None

    def test_us_format_not_matched(self):
        # 2025-03-15 is ISO, not DD/MM/YYYY — should return None
        assert _parse_rendered_date("2025-03-15") is None


# ── CSV parsing ──────────────────────────────────────────────────────────────

class TestParseCsv:
    def test_basic_csv(self):
        content = "Application Number,Status,Date Submitted\nAPP-001,Active,01/01/2025\n"
        rows = parse_csv(content)
        assert len(rows) == 1
        assert rows[0]["application number"] == "APP-001"
        assert rows[0]["status"] == "Active"
        assert rows[0]["date submitted"] == "01/01/2025"

    def test_strips_whitespace_from_keys_and_values(self):
        content = " Application Number , Status \n APP-002 , Pending \n"
        rows = parse_csv(content)
        assert rows[0]["application number"] == "APP-002"
        assert rows[0]["status"] == "Pending"

    def test_empty_values_become_none(self):
        content = "Application Number,Status\nAPP-003,\n"
        rows = parse_csv(content)
        assert rows[0]["status"] is None

    def test_empty_csv_returns_empty_list(self):
        content = "Application Number,Status\n"
        rows = parse_csv(content)
        assert rows == []

    def test_multiple_rows(self):
        content = "Application Number,Status\nAPP-001,Active\nAPP-002,Decided\nAPP-003,Withdrawn\n"
        rows = parse_csv(content)
        assert len(rows) == 3
        assert [r["application number"] for r in rows] == ["APP-001", "APP-002", "APP-003"]


# ── CSV record mapping ──────────────────────────────────────────────────────

class TestMapCsvRecord:
    GROUPS_CFG = {
        "development": {"label": "Development", "include_da": True, "include_ba": False, "include_plumb": False},
        "building": {"label": "Building", "include_da": False, "include_ba": True, "include_plumb": False},
    }

    def test_standard_record(self):
        row = {
            "application number": "MCU/2025/001",
            "date submitted": "15/03/2025",
            "description": "Material Change of Use",
            "status": "Active",
            "address": "123 Test St",
            "application type": "Material Change of Use",
            "suburb": "IPSWICH",
        }
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result is not None
        assert result["application_number"] == "MCU/2025/001"
        assert result["lodgement_date"] == date(2025, 3, 15)
        assert result["application_group"] == "Development"
        assert result["status"] == "Active"
        assert result["monitoring_status"] == "active"

    def test_building_group(self):
        row = {"application number": "BA/2025/001", "status": "Active"}
        result = map_csv_record(row, "building", self.GROUPS_CFG)
        assert result["application_group"] == "Building"

    def test_missing_app_number_returns_none(self):
        row = {"status": "Active", "description": "Test"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result is None

    def test_terminal_status_sets_closed(self):
        row = {"application number": "APP-001", "status": "Completed"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["monitoring_status"] == "closed"

    def test_alternate_column_names(self):
        row = {
            "app no.": "APP-002",
            "date lodged": "01/01/2025",
            "proposal": "Building work",
            "progress": "Under Assessment",
            "property address": "456 Main Rd",
            "type": "Building Works",
            "locality": "REDBANK",
        }
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["application_number"] == "APP-002"
        assert result["description"] == "Building work"
        assert result["status"] == "Under Assessment"
        assert result["location_address"] == "456 Main Rd"
        assert result["suburb"] == "REDBANK"

    def test_date_format_dd_mm_yy(self):
        row = {"application number": "APP-003", "date submitted": "15/03/25"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["lodgement_date"] == date(2025, 3, 15)

    def test_date_format_iso(self):
        row = {"application number": "APP-004", "date submitted": "2025-03-15"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["lodgement_date"] == date(2025, 3, 15)

    def test_invalid_date_sets_none(self):
        row = {"application number": "APP-005", "date submitted": "not-a-date"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["lodgement_date"] is None

    def test_strips_app_number_whitespace(self):
        row = {"application number": "  APP-006  "}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["application_number"] == "APP-006"

    def test_date_received_variant(self):
        row = {"application number": "APP-007", "date received": "20/06/2025"}
        result = map_csv_record(row, "development", self.GROUPS_CFG)
        assert result["lodgement_date"] == date(2025, 6, 20)


# ── Stage column mapping ────────────────────────────────────────────────────

class TestStageColumnMap:
    def test_all_stage_columns_are_valid_sql_identifiers(self):
        for stage_name, col_name in STAGE_COLUMN_MAP.items():
            assert col_name.isidentifier(), f"Invalid column name: {col_name}"
            assert col_name == col_name.lower(), f"Column should be lowercase: {col_name}"

    def test_known_stages_present(self):
        # Long-form names (Brisbane portal)
        assert "decision notice date" in STAGE_COLUMN_MAP
        assert "properly made date" in STAGE_COLUMN_MAP
        assert "record creation date" in STAGE_COLUMN_MAP
        # Short-form names (Development.i portals)
        assert "decision notice" in STAGE_COLUMN_MAP
        assert "confirmation period" in STAGE_COLUMN_MAP
        assert "confirmation notice" in STAGE_COLUMN_MAP

    def test_stage_count(self):
        # 9 long-form (Brisbane) + 6 short-form (Development.i portals)
        assert len(STAGE_COLUMN_MAP) == 15


# ── CLI parser ───────────────────────────────────────────────────────────────

class TestBuildParser:
    GROUPS = {
        "development": {"label": "Development"},
        "building": {"label": "Building"},
        "plumbing": {"label": "Plumbing"},
    }

    def test_default_args(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args([])
        assert args.full is False
        assert args.enrich is False
        assert args.monitor is False
        assert args.days == 30
        assert args.workers == 2
        assert args.headed is False

    def test_full_flag(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--full"])
        assert args.full is True

    def test_enrich_with_workers(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--enrich", "--workers", "4"])
        assert args.enrich is True
        assert args.workers == 4

    def test_group_choices_match_config(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--group", "plumbing"])
        assert args.group == "plumbing"

    def test_invalid_group_raises(self):
        parser = build_parser("Test Council", self.GROUPS)
        with pytest.raises(SystemExit):
            parser.parse_args(["--group", "invalid"])

    def test_mutually_exclusive_modes(self):
        parser = build_parser("Test Council", self.GROUPS)
        with pytest.raises(SystemExit):
            parser.parse_args(["--full", "--enrich"])

    def test_date_range_args(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--from-date", "2025-01-01", "--to-date", "2025-06-30"])
        assert args.from_date == "2025-01-01"
        assert args.to_date == "2025-06-30"

    def test_app_flag(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--app", "MCU/2025/001"])
        assert args.app == "MCU/2025/001"

    def test_monitor_with_limit(self):
        parser = build_parser("Test Council", self.GROUPS)
        args = parser.parse_args(["--monitor", "--limit", "50"])
        assert args.monitor is True
        assert args.limit == 50


# ── Integration: CSV → mapped records ────────────────────────────────────────

class TestCsvToRecordPipeline:
    """End-to-end test of CSV parsing into mapped records."""

    GROUPS_CFG = {
        "development": {"label": "Development", "include_da": True, "include_ba": False, "include_plumb": False},
    }

    SAMPLE_CSV = (
        "Application Number,Date Submitted,Description,Status,Address,Application Type,Suburb\n"
        "MCU/2025/001,15/03/2025,Material Change of Use - Dwelling House,Active,123 Test St,Material Change of Use,IPSWICH\n"
        "ROL/2025/002,20/03/2025,Reconfiguration - 1 into 2 lots,Under Assessment,456 Main Rd,Reconfiguring a lot,BOOVAL\n"
        "BA/2025/003,25/03/2025,Building Works - Shed,Completed,789 Oak Ave,Building Works,BRASSALL\n"
    )

    def test_full_pipeline(self):
        rows = parse_csv(self.SAMPLE_CSV)
        assert len(rows) == 3

        records = []
        for row in rows:
            mapped = map_csv_record(row, "development", self.GROUPS_CFG)
            if mapped:
                records.append(mapped)

        assert len(records) == 3

        # First record
        assert records[0]["application_number"] == "MCU/2025/001"
        assert records[0]["lodgement_date"] == date(2025, 3, 15)
        assert records[0]["monitoring_status"] == "active"

        # Second record
        assert records[1]["application_number"] == "ROL/2025/002"
        assert records[1]["suburb"] == "BOOVAL"

        # Third record — terminal status
        assert records[2]["application_number"] == "BA/2025/003"
        assert records[2]["monitoring_status"] == "closed"

    def test_csv_with_bom(self):
        """Development.i CSVs often have a UTF-8 BOM."""
        content = "\ufeffApplication Number,Status\nAPP-001,Active\n"
        rows = parse_csv(content)
        # The BOM may or may not be stripped by csv.DictReader, but
        # the value should still be accessible
        first_row = rows[0]
        # Check that app number is findable (key might have BOM prefix)
        app_num = first_row.get("application number") or first_row.get("\ufeffapplication number")
        assert app_num == "APP-001"


# ── Cross-council consistency ────────────────────────────────────────────────

class TestCrossCouncilConsistency:
    """Verify all councils share the same structural patterns."""

    def test_all_councils_have_same_group_structure(self):
        """Every group dict should have include_da, include_ba, include_plumb keys."""
        for slug, cfg in COUNCILS.items():
            for group_name, group_cfg in cfg["groups"].items():
                assert "include_da" in group_cfg, f"{slug}/{group_name} missing include_da"
                assert "include_ba" in group_cfg, f"{slug}/{group_name} missing include_ba"
                assert "include_plumb" in group_cfg, f"{slug}/{group_name} missing include_plumb"

    def test_no_duplicate_base_urls(self):
        urls = [cfg["base_url"] for cfg in COUNCILS.values()]
        assert len(urls) == len(set(urls)), "Duplicate base URLs found"

    def test_no_duplicate_parent_tables(self):
        tables = [cfg["parent_table"] for cfg in COUNCILS.values()]
        assert len(tables) == len(set(tables)), "Duplicate parent tables found"

    def test_no_duplicate_child_tables(self):
        tables = [cfg["child_table"] for cfg in COUNCILS.values()]
        assert len(tables) == len(set(tables)), "Duplicate child tables found"

    def test_all_filter_panel_selectors_are_css(self):
        for slug, cfg in COUNCILS.items():
            sel = cfg["filter_panel_selector"]
            assert sel.startswith("#") or sel.startswith("."), (
                f"{slug} filter_panel_selector should be a CSS selector: {sel}"
            )

    def test_filter_panel_needs_show_is_bool(self):
        for slug, cfg in COUNCILS.items():
            assert isinstance(cfg["filter_panel_needs_show"], bool), (
                f"{slug} filter_panel_needs_show must be a bool"
            )

    def test_has_detail_pages_is_bool(self):
        for slug, cfg in COUNCILS.items():
            assert isinstance(cfg["has_detail_pages"], bool)

    def test_description_addr_at_end_is_bool(self):
        for slug, cfg in COUNCILS.items():
            assert isinstance(cfg["description_addr_at_end"], bool)

    def test_ignore_https_errors_is_bool(self):
        for slug, cfg in COUNCILS.items():
            assert isinstance(cfg["ignore_https_errors"], bool)

    def test_westerndowns_ignores_https_errors(self):
        """Western Downs has an expired SSL cert."""
        assert COUNCILS["westerndowns"]["ignore_https_errors"] is True

    def test_all_others_dont_ignore_https_errors(self):
        for slug in ("ipswich", "redland", "sunshinecoast", "toowoomba"):
            assert COUNCILS[slug]["ignore_https_errors"] is False


# ── Toowoomba-format address extraction ─────────────────────────────────────

class TestExtractDescriptionAddressAtEnd:
    """Address-at-end format used by Toowoomba: 'Description - ADDRESS QLD POSTCODE'."""

    def test_basic_toowoomba_format(self):
        desc = "Material Change of Use - Code - 123 Main Street TOOWOOMBA QLD 4350"
        result = _extract_description_address(desc, addr_at_end=True)
        assert result == "123 Main Street TOOWOOMBA QLD 4350"

    def test_multiple_dashes_picks_last_address(self):
        desc = "Dual Occupancy - Code Impact - 45 Oak Ave HIGHFIELDS QLD 4352"
        result = _extract_description_address(desc, addr_at_end=True)
        assert result == "45 Oak Ave HIGHFIELDS QLD 4352"

    def test_no_qld_sentinel_returns_none(self):
        desc = "Material Change of Use - Some description without address"
        assert _extract_description_address(desc, addr_at_end=True) is None

    def test_addr_at_end_false_uses_start_format(self):
        desc = "123 Main Street BRISBANE QLD 4000 - Material Change of Use"
        result = _extract_description_address(desc, addr_at_end=False)
        assert result == "123 Main Street BRISBANE QLD 4000"

    def test_empty_returns_none_regardless_of_mode(self):
        assert _extract_description_address("", addr_at_end=True) is None
        assert _extract_description_address("", addr_at_end=False) is None

    def test_toowoomba_hyphenated_street(self):
        desc = "Operational Works - Civil - 1-5 Industrial Drive CHARLTON QLD 4350"
        result = _extract_description_address(desc, addr_at_end=True)
        assert result == "1-5 Industrial Drive CHARLTON QLD 4350"
