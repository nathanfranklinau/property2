#!/usr/bin/env python3
"""Capture data from the modal by clicking Details button."""

import sys
import json
from playwright.sync_api import sync_playwright

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"

print(f"\nCapturing modal data for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    # Load search page
    print("1. Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(5000)

    # Search for application
    print(f"2. Searching for {app_num}...")
    search_inputs = page.locator("input[type='text']")
    for i in range(search_inputs.count()):
        placeholder = search_inputs.nth(i).get_attribute("placeholder") or ""
        if "search" in placeholder.lower():
            search_inputs.nth(i).fill(app_num)
            search_inputs.nth(i).press("Enter")
            break

    page.wait_for_timeout(5000)

    # Find and click Details button for our application
    print(f"3. Clicking Details button for {app_num}...")
    detail_buttons = page.locator(f"a[data-id='{app_num}'].application-moreinfo")

    if detail_buttons.count() > 0:
        detail_buttons.first.click()
        page.wait_for_timeout(3000)

        # Check for modal
        modal = page.locator(".modal.in, .modal.show, [role='dialog']")
        if modal.count() > 0:
            print("✓ Modal appeared\n")

            # Get modal content
            modal_body = page.locator(".modal-body, .modal-content")
            modal_text = modal_body.text_content() if modal_body.count() > 0 else ""

            print("Modal content:")
            print(modal_text[:2000])

            # Get all data from modal
            modal_html = modal_body.evaluate("el => el.innerHTML") if modal_body.count() > 0 else ""

            # Look for specific fields
            print("\n\nSearching for specific fields in modal...")
            fields_to_find = ["status", "decision", "progress", "application type", "address", "applicant"]

            for field in fields_to_find:
                if field.lower() in modal_text.lower():
                    print(f"  ✓ Found: {field}")

            # Save modal HTML for inspection
            with open("/tmp/modal_content.html", "w") as f:
                f.write(f"<html><body>{modal_html}</body></html>")
            print("\n✓ Saved modal HTML to /tmp/modal_content.html")
        else:
            print("❌ Modal did not appear")
            print("Available elements:")
            all_divs = page.locator("div[class*='modal'], div[role='dialog']")
            print(f"Found {all_divs.count()} modal-like divs")

    else:
        print(f"❌ No Details button found for {app_num}")

    browser.close()
