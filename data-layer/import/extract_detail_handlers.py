#!/usr/bin/env python3
"""Extract onclick/data attributes from Details buttons."""

import sys
from playwright.sync_api import sync_playwright
import re

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"

print(f"\nFinding detail handlers for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    # Go to search page
    print("1. Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(5000)

    # Search
    print(f"2. Searching for {app_num}...")
    search_inputs = page.locator("input[type='text']")
    for i in range(search_inputs.count()):
        placeholder = search_inputs.nth(i).get_attribute("placeholder") or ""
        if "search" in placeholder.lower() or "application" in placeholder.lower():
            search_inputs.nth(i).fill(app_num)
            search_inputs.nth(i).press("Enter")
            break

    page.wait_for_timeout(5000)

    # Find details buttons
    print("\n3. Finding Details buttons...\n")
    detail_buttons = page.locator("a:has-text('Details'), button:has-text('Details')")
    print(f"Found {detail_buttons.count()} Details buttons\n")

    for i in range(detail_buttons.count()):
        btn = detail_buttons.nth(i)

        # Get all attributes
        onclick = btn.get_attribute("onclick") or ""
        data_attrs = {}

        # Get all data-* attributes
        for attr in ["data-id", "data-app-id", "data-application-id", "data-app", "data-name"]:
            val = btn.get_attribute(attr)
            if val:
                data_attrs[attr] = val

        inner_html = btn.evaluate("el => el.innerHTML") or ""
        outer_html = btn.evaluate("el => el.outerHTML") or ""

        print(f"Button {i}:")
        print(f"  onclick: {onclick[:100]}")
        print(f"  data attributes: {data_attrs}")
        print(f"  innerHTML: {inner_html[:100]}")
        print(f"  outerHTML: {outer_html[:150]}\n")

        # Try to extract application ID from onclick
        if "(" in onclick:
            params = re.findall(r"'([^']*)'|\"([^\"]*)\"", onclick)
            if params:
                print(f"  Extracted params: {params}\n")

    # Also check the HTML content
    print("\n4. Raw HTML of search results:\n")
    body_html = page.locator("body").evaluate("el => el.innerHTML")

    # Find all data attributes in the page
    print("Looking for data attributes containing application IDs:")
    app_id_matches = re.findall(r'data-[a-z-]*["\']?([0-9a-zA-Z/]+)["\']?', body_html, re.IGNORECASE)
    for match in set(app_id_matches)[:10]:
        print(f"  {match}")

    browser.close()
