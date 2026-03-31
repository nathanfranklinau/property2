#!/usr/bin/env python3
"""Debug Ipswich detail page extraction."""

import sys
from playwright.sync_api import sync_playwright

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"
url = f"https://developmenti.ipswich.qld.gov.au/Home/ApplicationDetailsView?id={app_num}&type=plan_development_apps"

print(f"\nDebug: {app_num}\nURL: {url}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Try to load with very long timeout
    try:
        page.goto(url, timeout=120000)
        print("✓ Page loaded")
    except Exception as e:
        print(f"⚠️  Load error: {e}")
        print("Attempting to read what's on page anyway...")

    # Wait for JS
    page.wait_for_timeout(5000)

    # Check current URL
    print(f"Current URL: {page.url}")

    # Look for h5 labels
    h5s = page.locator("h5")
    print(f"\nFound {h5s.count()} h5 elements:")
    for i in range(min(h5s.count(), 15)):
        text = h5s.nth(i).text_content().strip()
        print(f"  {i+1}. {text}")

    # Look for table rows
    rows = page.locator("table.table-bordered tr")
    print(f"\nFound {rows.count()} table rows")

    # Look for any text content
    body_text = page.locator("body").text_content()
    print(f"\nPage text length: {len(body_text)} chars")
    print(f"First 500 chars:\n{body_text[:500]}")

    browser.close()
