#!/usr/bin/env python3
"""Dump full HTML of detail page."""

import sys
from playwright.sync_api import sync_playwright

app_num = sys.argv[1] if len(sys.argv) > 1 else "4722/2026/ADP"
url = f"https://developmenti.ipswich.qld.gov.au/Home/ApplicationDetailsView?id={app_num}&type=plan_development_apps"

print(f"Loading: {app_num}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    try:
        page.goto(url, timeout=120000)  # Very long timeout
    except Exception as e:
        print(f"Error (will try anyway): {e}")

    page.wait_for_timeout(5000)

    html = page.content()

    # Save to file
    with open(f"/tmp/ipswich_{app_num.replace('/', '_')}.html", "w") as f:
        f.write(html)

    print(f"Saved HTML to /tmp/ipswich_{app_num.replace('/', '_')}.html")
    print(f"File size: {len(html)} bytes")

    # Print first 5000 chars
    print("\nFirst 5000 chars of HTML:")
    print(html[:5000])

    browser.close()
