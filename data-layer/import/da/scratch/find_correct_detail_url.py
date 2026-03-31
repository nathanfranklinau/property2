#!/usr/bin/env python3
"""Find the correct detail page URL by searching for an application."""

import sys
from playwright.sync_api import sync_playwright
import time

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"

print(f"\nSearching for application: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Show browser so you can see it
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    # Go to search page
    print("1. Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)

    # Search for the application
    print(f"2. Searching for {app_num}...")
    search_input = page.locator("#searchTerm, input[name='searchTerm'], input[placeholder*='search'], input[placeholder*='application']")

    if search_input.count() > 0:
        search_input.first.fill(app_num)
        search_input.first.press("Enter")
        page.wait_for_timeout(3000)
        print("3. Search submitted")
    else:
        print("❌ Could not find search input")

    # Wait for results to load
    print("4. Waiting for results...")
    page.wait_for_timeout(5000)

    # Look for a clickable result
    results = page.locator("tr, li, div.result, a[href*='ApplicationDetailsView']")
    print(f"   Found {results.count()} potential results")

    # Try to find and click the application number
    print("5. Looking for clickable application link...")
    links = page.locator(f"a:has-text('{app_num}')")
    if links.count() > 0:
        print(f"   Found link with text '{app_num}'")
        href = links.first.get_attribute("href")
        print(f"   ✓ DETAIL PAGE URL: {href}")

        # Navigate to it
        page.goto(href)
        page.wait_for_timeout(5000)
        print(f"   Current URL after click: {page.url}")
    else:
        print(f"   ❌ No link found for '{app_num}'")

        # Try clicking any link
        all_links = page.locator("a")
        print(f"   Total links on page: {all_links.count()}")
        for i in range(min(10, all_links.count())):
            text = all_links.nth(i).text_content().strip()
            href = all_links.nth(i).get_attribute("href") or ""
            if "ApplicationDetailsView" in href or app_num in text:
                print(f"   {i}. {text[:50]:50} → {href}")

    # Show final URL
    print(f"\n6. Final URL in browser: {page.url}")
    print("\n✓ Browser is open - inspect it manually if needed")
    print("Press Ctrl+C when done\n")

    time.sleep(30)  # Keep browser open for inspection
    browser.close()
