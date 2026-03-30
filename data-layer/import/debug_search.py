#!/usr/bin/env python3
"""Debug search results for an application."""

import sys
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

app_num = sys.argv[1] if len(sys.argv) > 1 else "10157/2018/MAPDA/A"

print(f"\nDebugging search for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    # Go to search page
    print("1. Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)
    
    # Search
    print(f"2. Searching for {app_num}...")
    search_inputs = page.locator("input[type='text']")
    for i in range(search_inputs.count()):
        placeholder = (search_inputs.nth(i).get_attribute("placeholder") or "").lower()
        if "search" in placeholder or "application" in placeholder:
            search_inputs.nth(i).fill(app_num)
            search_inputs.nth(i).press("Enter")
            break
    
    page.wait_for_timeout(3000)
    
    # Check what we got
    results_container = page.locator(".search-results, #search-results, table tbody")
    print(f"\nResults containers found: {results_container.count()}")
    
    # Check for "no results" message
    no_results = page.locator("text=No results found")
    if no_results.count() > 0:
        print(f"✗ Search returned 'No results found'")
    else:
        print(f"✓ Search has results")
    
    # Look for detail buttons with this app number
    detail_buttons = page.locator(f"a[data-id='{app_num}']")
    print(f"\nDetail buttons with data-id='{app_num}': {detail_buttons.count()}")
    
    # Look for any links/buttons with the app number in text
    app_links = page.locator(f"a:has-text('{app_num}')")
    print(f"Links with text containing '{app_num}': {app_links.count()}")
    for i in range(min(3, app_links.count())):
        link = app_links.nth(i)
        href = link.get_attribute("href") or ""
        classes = link.get_attribute("class") or ""
        print(f"  Link {i}: href='{href}' class='{classes}'")
    
    # Look for application-moreinfo buttons
    more_info = page.locator("a.application-moreinfo")
    print(f"\nTotal 'application-moreinfo' buttons: {more_info.count()}")
    if more_info.count() > 0:
        for i in range(min(3, more_info.count())):
            link = more_info.nth(i)
            data_id = link.get_attribute("data-id") or ""
            text = link.text_content().strip()[:40]
            print(f"  Button {i}: data-id='{data_id}' text='{text}'")
    
    browser.close()
    print("\n✓ Done")
