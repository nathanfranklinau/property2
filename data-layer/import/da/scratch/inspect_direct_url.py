#!/usr/bin/env python3
"""Access application detail page directly via URL."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

app_num = sys.argv[1] if len(sys.argv) > 1 else "14482/2025/MCU"

print(f"\nAccessing detail page for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    # Try direct URL
    url = f"https://developmenti.ipswich.qld.gov.au/Home/ApplicationDetailsView?id={app_num}"
    print(f"1. Loading: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=10000)
        page.wait_for_timeout(2000)
        print(f"✓ Page loaded")
        print(f"  Current URL: {page.url}")
        print(f"  Page title: {page.title()}")
        
        # Check for divPrint (modal container)
        div_print = page.locator("#divPrint")
        if div_print.count() > 0:
            print(f"\n✓ Found #divPrint container")
            
            # Look for Associated Properties
            props = div_print.locator("a[href*='PropertyDetailsView']")
            print(f"  Property links found: {props.count()}")
            for i in range(props.count()):
                link = props.nth(i)
                href = link.get_attribute("href") or ""
                text = link.text_content().strip()
                print(f"    {i+1}. {text}")
                print(f"       href: {href}")
        else:
            print(f"✗ No #divPrint found")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    browser.close()
