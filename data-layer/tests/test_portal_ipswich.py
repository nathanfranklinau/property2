"""Functional tests for the Ipswich Development.i portal.

These tests connect to the live portal to detect when the site changes its
markup, CSV structure, or field layout in ways that would break our importer.

Run with:
    pytest tests/test_portal_ipswich.py -v -m portal

Mark: @pytest.mark.portal
All tests in this file require network access and are slow (~30s each).
They should NOT be run as part of the normal unit test suite.
"""

import csv
import io
import time

import pytest
from playwright.sync_api import sync_playwright, Page

BASE_URL   = "https://developmenti.ipswich.qld.gov.au"
SEARCH_URL = f"{BASE_URL}/Home/MapSearch"
DETAIL_URL = f"{BASE_URL}/Home/ApplicationDetailsView"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ── Expected CSV column headers ───────────────────────────────────────────────

EXPECTED_CSV_COLUMNS = {
    "application group",
    "application number",
    "full description",
    "land parcel status",
    "progress",
    "stage/decision",
    "application type",
    "assessment level",
    "use",
    "date submitted",
    "date decided",
}

# ── Decided application fixtures (frozen — these will not change) ─────────────
#
# Fetched 2026-03-30 from the Ipswich portal. All have stage/decision=Approved
# and a date decided, so their field values are permanently fixed.
#
# Fields tested:
#   application_number  — unique identifier, immutable
#   full_description    — text of the application, immutable once decided
#   application_type    — type classification, immutable once decided
#   assessment_level    — Code / Impact / Other, immutable once decided
#   date_submitted      — lodgement date, immutable
#   date_decided        — decision date, immutable

DECIDED_FIXTURES = [
    {
        "application_number": "1087/2026/OW",
        "full_description": "Landscaping",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "28/1/2026",
        "date_decided": "26/2/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "535/2026/OW",
        "full_description": "Internal Landscaping and Streetscaping",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "16/1/2026",
        "date_decided": "23/2/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "15/2026/OW",
        "full_description": "Road Work, Stormwater, Earthworks",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "2/1/2026",
        "date_decided": "10/3/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "13821/2025/OW",
        "full_description": "Landscaping - Streetscaping and Internal Works",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "8/12/2025",
        "date_decided": "24/12/2025",
        "stage_decision": "Approved",
    },
    {
        "application_number": "13803/2025/OW",
        "full_description": "Stormwater and Driveway",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "5/12/2025",
        "date_decided": "13/1/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "13702/2025/OW",
        "full_description": "Park Embellishment Landscaping - Archer Street Park",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "3/12/2025",
        "date_decided": "23/2/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "12039/2023/MAEXT/A",
        "full_description": "Extension to Currency Period Application - Earthworks",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "3/12/2025",
        "date_decided": "11/3/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "13646/2025/OW",
        "full_description": "Streetscape Landscaping and Drainage Channel - Stage 2",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "2/12/2025",
        "date_decided": "14/1/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "13645/2025/OW",
        "full_description": "Landscaping - Drainage Channel (Stage 1)",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "2/12/2025",
        "date_decided": "12/1/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "12974/2025/OW",
        "full_description": "Earthworks, Roadworks and Stormwater Drainage",
        "application_type": "Operational Works",
        "assessment_level": "Code",
        "date_submitted": "14/11/2025",
        "date_decided": "24/12/2025",
        "stage_decision": "Approved",
    },
    {
        "application_number": "2175/2026/SSPRV",
        "full_description": "Fischer Road Upgrade - Stage 3 - Lot 178 on SP358097",
        "application_type": "Plan Sealing",
        "assessment_level": "Other",
        "date_submitted": "16/2/2026",
        "date_decided": "18/2/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "2770/2023/MAEXT/A",
        "full_description": "Extension to Currency Period Application - Landscaping",
        "application_type": "Operational Works; Modification/Extension",
        "assessment_level": "Other",
        "date_submitted": "19/2/2026",
        "date_decided": "3/3/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "2382/2024/PDAEPC/A",
        "full_description": (
            "Pre-Construction Certification - White Rock Estate - Precinct 2 - "
            "Bulk Earthworks in accordance with Condition N/A of Development Permit "
            "2382/2024/PDA"
        ),
        "application_type": "PDA Preconstruction Submission",
        "assessment_level": "Other",
        "date_submitted": "13/11/2025",
        "date_decided": "17/12/2025",
        "stage_decision": "Approved",
    },
    {
        "application_number": "2382/2024/PDAEPC/B",
        "full_description": (
            "Pre-Construction Certification - White Rock Stage 6A - Rate 3 Public Lighting - "
            "2 Lot Subdivision in accordance with Condition Number: As defined in Arcadis' "
            "Approval Condition Register (EHA-30083819.2-P2-01-AAR Rev 1 dated 24/10/2025) "
            "of Development Permit 2382/2024/PDA"
        ),
        "application_type": "PDA Preconstruction Submission",
        "assessment_level": "Other",
        "date_submitted": "5/3/2026",
        "date_decided": "19/3/2026",
        "stage_decision": "Approved",
    },
    {
        "application_number": "14040/2021/PDAEPC/I",
        "full_description": (
            "Pre-Construction Certification - Botanica, Precinct B - Early Bulk Earthworks "
            "to Botanica Precinct B as per condition 48 - to facilitate HV relocation in "
            "accordance with Condition As noted on certifiers pre-construction forms of "
            "Development Permit 14040/2021/MAPDA/B"
        ),
        "application_type": "PDA Preconstruction Submission",
        "assessment_level": "Other",
        "date_submitted": "24/11/2025",
        "date_decided": "18/12/2025",
        "stage_decision": "Approved",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_browser_ctx(playwright):
    browser = playwright.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA)
    return browser, ctx


def _set_filters(page: Page, from_date: str, to_date: str) -> None:
    """Apply Development group + date range filters on the MapSearch page."""
    page.wait_for_selector("#search-filters", state="attached", timeout=20000)
    time.sleep(0.5)

    # Force-show the hidden filter panel
    page.evaluate("document.querySelector('#search-filters').style.display = 'block';")
    time.sleep(0.5)

    # Set group = Development
    page.evaluate("""() => {
        const sel = document.getElementById('filter-application-group');
        if (sel) { sel.value = 'development'; sel.dispatchEvent(new Event('change', {bubbles: true})); }
    }""")
    time.sleep(2)

    # Open date dropdown + set Submitted radio
    page.evaluate("""() => {
        const d = document.getElementById('date-range-dropdown');
        if (d) d.style.display = 'block';
        const r = document.getElementById('status-submitted');
        if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true})); }
    }""")
    time.sleep(0.3)

    # Set date range via daterangepicker
    page.evaluate(f"""() => {{
        var jq = window.jQuery || window.$;
        var el = jq('#dateRangeInput')[0];
        var picker = jq(el).data('daterangepicker');
        picker.setStartDate('{from_date}'); picker.setEndDate('{to_date}');
        var v = picker.startDate.format('DD/MM/YYYY') + picker.locale.separator + picker.endDate.format('DD/MM/YYYY');
        jq(el).val(v); jq(el).trigger('apply.daterangepicker', picker);
    }}""")
    time.sleep(2)

    # Re-hide the panel so it doesn't intercept the download button
    page.evaluate("document.querySelector('#search-filters').style.display = 'none';")


def _download_csv(page: Page) -> list[dict]:
    """Click the CSV download button and return normalised rows."""
    with page.expect_download(timeout=120000) as dl_info:
        page.locator(".download-csv").click()
    content = open(dl_info.value.path(), encoding="utf-8-sig").read()
    reader = csv.DictReader(io.StringIO(content))
    return [
        {k.strip().lower(): (v.strip() if v and v.strip() else None) for k, v in row.items() if k}
        for row in reader
    ]


def _get_modal_field(modal, label: str) -> str | None:
    """Extract a field value from an applicationModal (h5 + sibling div)."""
    h5 = modal.locator(f"h5:has-text('{label}')")
    if h5.count() == 0:
        return None
    parent = h5.first.locator("xpath=..")
    sibling = parent.locator("xpath=following-sibling::div")
    if sibling.count() > 0:
        text = sibling.first.text_content().strip()
        return text if text else None
    return None


# ── pytest fixture: shared CSV download ───────────────────────────────────────

@pytest.fixture(scope="module")
def ipswich_csv_rows():
    """Download the Ipswich CSV once per test module and return all rows."""
    with sync_playwright() as p:
        browser, ctx = _make_browser_ctx(p)
        page = ctx.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        _set_filters(page, "01/11/2025", "30/03/2026")
        rows = _download_csv(page)
        browser.close()
    return {r["application number"]: r for r in rows if r.get("application number")}


# ── CSV structure tests ────────────────────────────────────────────────────────

@pytest.mark.portal
class TestIpswichCsvStructure:
    """Verify the Ipswich CSV download still has the expected column set.

    If any of these fail, the portal has changed its CSV export format
    and the importer's column-name mappings need updating.
    """

    def test_csv_contains_all_expected_columns(self, ipswich_csv_rows):
        if not ipswich_csv_rows:
            pytest.skip("No rows returned from portal")
        sample_row = next(iter(ipswich_csv_rows.values()))
        actual_columns = set(sample_row.keys())
        missing = EXPECTED_CSV_COLUMNS - actual_columns
        assert not missing, (
            f"CSV is missing columns: {missing}\n"
            f"Actual columns: {actual_columns}"
        )

    def test_csv_has_no_unexpected_columns(self, ipswich_csv_rows):
        """Alerts if the portal adds new columns we should be capturing."""
        if not ipswich_csv_rows:
            pytest.skip("No rows returned from portal")
        sample_row = next(iter(ipswich_csv_rows.values()))
        actual_columns = set(sample_row.keys())
        unexpected = actual_columns - EXPECTED_CSV_COLUMNS
        assert not unexpected, (
            f"Portal added new CSV columns — check if importer should capture them: {unexpected}"
        )

    def test_csv_returns_rows(self, ipswich_csv_rows):
        assert len(ipswich_csv_rows) > 0, "CSV download returned no rows"

    def test_application_group_column_values(self, ipswich_csv_rows):
        """Every row should belong to the Development group."""
        for app_num, row in ipswich_csv_rows.items():
            assert row.get("application group") == "Development", (
                f"{app_num}: expected application group='Development', got {row.get('application group')!r}"
            )

    def test_assessment_level_values_are_known(self, ipswich_csv_rows):
        """Assessment level should only ever be Code, Impact, or Other."""
        known = {"Code", "Impact", "Other", None}
        unknown = {
            row.get("assessment level")
            for row in ipswich_csv_rows.values()
            if row.get("assessment level") not in known
        }
        assert not unknown, f"Unknown assessment level values: {unknown}"

    def test_stage_decision_values_are_known(self, ipswich_csv_rows):
        """Stage/decision values seen in the portal — alerts if new ones appear."""
        known_stages = {
            "Approved", "Information Response", "Decision",
            "Confirmation Period", "Initial Application Review",
            "Information Request", "Current Period Stopped",
            "Referral", "Awaiting Outstanding Information",
            "Outstanding Issues Response", "Initial Assessment",
            "Decision Stage", "EDQ Review & Endorsement",
            "Info Response", "SSP Not Properly Made", "Action Notice",
            "Outstanding Issues Request", "Public Notification",
            "Not Properly Made (Awaiting Advice)", "Claim Approved - MEDQ",
            "Info Request", "Request Complete", "Final Assessment",
            None,
        }
        actual = {row.get("stage/decision") for row in ipswich_csv_rows.values()}
        unknown = actual - known_stages
        assert not unknown, (
            f"New stage/decision values appeared — update importer mapping: {unknown}"
        )


# ── Fixture-record tests ───────────────────────────────────────────────────────

@pytest.mark.portal
class TestIpswichDecidedFixtures:
    """Verify specific decided application records haven't changed.

    These apps are permanently approved — their field values are frozen.
    A failure here means the portal changed something that should be immutable,
    or the portal's CSV export format changed.
    """

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_appears_in_csv(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        assert app_num in ipswich_csv_rows, (
            f"Application {app_num} not found in CSV — "
            "portal may have removed it or the date range needs adjusting"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_full_description(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("full description") == fixture["full_description"], (
            f"{app_num}: full description changed\n"
            f"  expected: {fixture['full_description']!r}\n"
            f"  actual:   {row.get('full description')!r}"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_application_type(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("application type") == fixture["application_type"], (
            f"{app_num}: application type changed\n"
            f"  expected: {fixture['application_type']!r}\n"
            f"  actual:   {row.get('application type')!r}"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_assessment_level(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("assessment level") == fixture["assessment_level"], (
            f"{app_num}: assessment level changed\n"
            f"  expected: {fixture['assessment_level']!r}\n"
            f"  actual:   {row.get('assessment level')!r}"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_stage_decision(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("stage/decision") == fixture["stage_decision"], (
            f"{app_num}: stage/decision changed\n"
            f"  expected: {fixture['stage_decision']!r}\n"
            f"  actual:   {row.get('stage/decision')!r}"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_date_submitted(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("date submitted") == fixture["date_submitted"], (
            f"{app_num}: date submitted changed\n"
            f"  expected: {fixture['date_submitted']!r}\n"
            f"  actual:   {row.get('date submitted')!r}"
        )

    @pytest.mark.parametrize("fixture", DECIDED_FIXTURES, ids=[f["application_number"] for f in DECIDED_FIXTURES])
    def test_decided_app_date_decided(self, fixture, ipswich_csv_rows):
        app_num = fixture["application_number"]
        if app_num not in ipswich_csv_rows:
            pytest.skip(f"{app_num} not in CSV")
        row = ipswich_csv_rows[app_num]
        assert row.get("date decided") == fixture["date_decided"], (
            f"{app_num}: date decided changed\n"
            f"  expected: {fixture['date_decided']!r}\n"
            f"  actual:   {row.get('date decided')!r}"
        )


# ── Detail page DOM structure tests ───────────────────────────────────────────

# A single stable decided app used for DOM structure verification.
# Chosen because it has all fields populated including assessment officer.
DETAIL_TEST_APP = "1087/2026/OW"
DETAIL_TEST_EXPECTED = {
    "Full Description:": "Landscaping",
    "Progress:": "In Progress",
    "Stage/Decision:": "Approved",
    "Application Type:": "Operational Works",
    "Assessment Level:": "Code",
    "Date Submitted:": "28/1/2026",
    "Date Decided:": "26/2/2026",
}


@pytest.fixture(scope="module")
def ipswich_detail_page_data():
    """Open the Details modal for DETAIL_TEST_APP and return extracted fields.

    The ApplicationDetailsView standalone URL requires an established session and
    app-number routing that doesn't work for direct navigation. Instead, we filter
    the search results to show the target app and click its modal trigger button.
    DETAIL_TEST_APP was submitted 28/1/2026 so we filter for Jan-Feb 2026 to ensure
    it appears in results.
    """
    with sync_playwright() as p:
        browser, ctx = _make_browser_ctx(p)
        page = ctx.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        _set_filters(page, "01/01/2026", "28/02/2026")

        # Click the modal trigger for our target app
        btn = page.locator(f'a.application-moreinfo[data-id="{DETAIL_TEST_APP}"]')
        if btn.count() == 0:
            browser.close()
            return {"_not_found": True}
        btn.click()
        page.wait_for_selector("#applicationModal h5", timeout=15000)
        time.sleep(1)

        modal = page.locator("#applicationModal")
        data = {}
        for label in DETAIL_TEST_EXPECTED:
            data[label] = _get_modal_field(modal, label)

        data["_has_stages_table"] = modal.locator("table").count() > 0
        data["_has_properties_section"] = (
            modal.locator("a[href*='PropertyDetailsView']").count() > 0
        )
        data["_page_title"] = page.title()
        browser.close()
    return data


@pytest.mark.portal
class TestIpswichDetailPageStructure:
    """Verify the Details modal structure for a known decided app.

    If any h5 label tests fail, the portal has renamed or restructured its
    field labels — the importer's extract_detail() function will be broken.
    """

    def test_detail_modal_loads(self, ipswich_detail_page_data):
        assert not ipswich_detail_page_data.get("_not_found"), (
            f"App {DETAIL_TEST_APP!r} not found in Jan-Feb 2026 search results"
        )
        assert "Error" not in (ipswich_detail_page_data.get("_page_title") or ""), (
            "Search page returned an error"
        )

    @pytest.mark.parametrize("label,expected_value", DETAIL_TEST_EXPECTED.items())
    def test_detail_field_present_and_correct(self, label, expected_value, ipswich_detail_page_data):
        actual = ipswich_detail_page_data.get(label)
        assert actual is not None, (
            f"Field label {label!r} not found on detail page — "
            "portal may have renamed or restructured this field"
        )
        assert actual == expected_value, (
            f"Field {label!r} value changed\n"
            f"  expected: {expected_value!r}\n"
            f"  actual:   {actual!r}"
        )

    def test_detail_modal_has_stages_table(self, ipswich_detail_page_data):
        assert ipswich_detail_page_data["_has_stages_table"], (
            "No table found in Details modal — "
            "portal may have restructured the milestone dates section"
        )

    def test_detail_modal_has_associated_properties(self, ipswich_detail_page_data):
        assert ipswich_detail_page_data["_has_properties_section"], (
            "No PropertyDetailsView links found in Details modal — "
            "portal may have restructured the associated properties section"
        )


# ── Filter mechanism tests ─────────────────────────────────────────────────────

@pytest.mark.portal
class TestIpswichFilterMechanism:
    """Verify the search filter mechanism still works as expected.

    These catch UI changes that would break the CSV download automation
    without necessarily changing the CSV format.
    """

    def test_filter_panel_selector_exists(self):
        with sync_playwright() as p:
            browser, ctx = _make_browser_ctx(p)
            page = ctx.new_page()
            page.goto(SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            exists = page.locator("#search-filters").count()
            browser.close()
        assert exists > 0, "#search-filters panel not found — filter panel selector has changed"

    def test_group_select_exists(self):
        with sync_playwright() as p:
            browser, ctx = _make_browser_ctx(p)
            page = ctx.new_page()
            page.goto(SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            exists = page.locator("#filter-application-group").count()
            browser.close()
        assert exists > 0, "#filter-application-group select not found"

    def test_group_select_has_development_option(self):
        with sync_playwright() as p:
            browser, ctx = _make_browser_ctx(p)
            page = ctx.new_page()
            page.goto(SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.evaluate("document.querySelector('#search-filters').style.display = 'block';")
            time.sleep(0.5)
            options = page.evaluate("""() => {
                const sel = document.getElementById('filter-application-group');
                return sel ? Array.from(sel.options).map(o => o.value) : [];
            }""")
            browser.close()
        assert "development" in options, (
            f"'development' option not found in group select — options: {options}"
        )

    def test_daterangepicker_input_exists(self):
        with sync_playwright() as p:
            browser, ctx = _make_browser_ctx(p)
            page = ctx.new_page()
            page.goto(SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            exists = page.locator("#dateRangeInput").count()
            browser.close()
        assert exists > 0, "#dateRangeInput not found — date range selector has changed"

    def test_csv_download_button_exists(self):
        with sync_playwright() as p:
            browser, ctx = _make_browser_ctx(p)
            page = ctx.new_page()
            page.goto(SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=30000)
            exists = page.locator(".download-csv").count()
            browser.close()
        assert exists > 0, ".download-csv button not found — download mechanism has changed"
