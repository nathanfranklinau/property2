#!/usr/bin/env python3
"""Analyze search results page to find detail link URLs."""

import sys
from playwright.sync_api import sync_playwright
import json

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"

print(f"\nAnalyzing search results for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    # Go to search page
    print("Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(5000)

    # Search
    print(f"Searching for {app_num}...")
    search_inputs = page.locator("input[type='text']")
    for i in range(search_inputs.count()):
        placeholder = search_inputs.nth(i).get_attribute("placeholder") or ""
        if "search" in placeholder.lower() or "application" in placeholder.lower():
            search_inputs.nth(i).fill(app_num)
            search_inputs.nth(i).press("Enter")
            break

    page.wait_for_timeout(5000)

    # Dump all links
    print("\nAll links on search results page:\n")
    links = page.locator("a")
    found_detail_link = False

    for i in range(links.count()):
        link = links.nth(i)
        text = link.text_content().strip()[:50]
        href = link.get_attribute("href") or ""

        if href and ("ApplicationDetailsView" in href or "Details" in href or app_num in href):
            print(f"✓ DETAIL LINK FOUND:")
            print(f"  Text: {text}")
            print(f"  URL: {href}")
            found_detail_link = True
        elif text == app_num or app_num in text:
            print(f"✓ APP NUMBER LINK:")
            print(f"  Text: {text}")
            print(f"  URL: {href}")
            found_detail_link = True

    if not found_detail_link:
        print("No detail links found. All links:")
        for i in range(min(20, links.count())):
            link = links.nth(i)
            text = link.text_content().strip()[:40]
            href = link.get_attribute("href") or ""
            print(f"  {i}. {text:40} → {href[:80]}")

    browser.close()
