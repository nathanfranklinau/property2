#!/usr/bin/env python3
"""Inspect actual portal HTML structure."""

import sys
from playwright.sync_api import sync_playwright

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"
url = f"https://developmenti.ipswich.qld.gov.au/Home/ApplicationDetailsView?id={app_num}&type=plan_development_apps"

print(f"\n{'='*100}\nLoading: {app_num}\n{'='*100}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Show browser
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    print(f"Loading {url}")
    page.goto(url)  # No wait_until - just load

    print("Page loaded. Waiting 10 seconds for JS to render...")
    page.wait_for_timeout(10000)

    print(f"\nFinal URL: {page.url}")
    print(f"Page title: {page.title()}\n")

    # Get ALL text on page
    body_text = page.locator("body").text_content()
    print(f"Page text ({len(body_text)} chars):\n")
    print(body_text[:2000])
    print("\n" + "="*100)

    # Get all h5 and h6 elements
    h5s = page.locator("h5")
    h6s = page.locator("h6")
    print(f"\nFound {h5s.count()} h5 elements, {h6s.count()} h6 elements\n")

    for i in range(min(20, h5s.count())):
        text = h5s.nth(i).text_content().strip()
        print(f"h5[{i}]: {text}")

    # Try to find ANY divs with text
    print("\n" + "="*100)
    print("\nSearching for divs with 'Progress' or 'Status':")
    divs = page.locator("div:has-text('Progress'), div:has-text('Status')")
    for i in range(min(10, divs.count())):
        text = divs.nth(i).text_content().strip()
        print(f"  {text[:80]}")

    browser.close()

print("\n✓ Done - check browser window for visual inspection")
