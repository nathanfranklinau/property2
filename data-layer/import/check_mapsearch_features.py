#!/usr/bin/env python3
"""Check MapSearch for pagination, filters, or other ways to find all apps."""

from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)
    
    # Check for pagination
    pagination = page.locator(".pagination, .pager, [aria-label*='Page']")
    print(f"Pagination controls found: {pagination.count()}")
    
    # Check for "Show all" or "Load more" buttons
    buttons = page.locator("button")
    print(f"\nAll buttons:")
    for i in range(buttons.count()):
        text = buttons.nth(i).text_content().strip()[:50]
        if text:
            print(f"  {text}")
    
    # Check for table with rows
    rows = page.locator("tbody tr")
    print(f"\nTable rows: {rows.count()}")
    
    # Check for filter panel
    filters = page.locator("#search-filters")
    print(f"\nFilter panel visible: {filters.count() > 0}")
    if filters.count() > 0:
        filter_inputs = filters.locator("input, select")
        print(f"Filter inputs: {filter_inputs.count()}")
    
    browser.close()
