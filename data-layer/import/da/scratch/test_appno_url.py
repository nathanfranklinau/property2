#!/usr/bin/env python3
"""Test the appNo URL format."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT
import urllib.parse

app_num = "14482/2025/MCU"
encoded = urllib.parse.quote(app_num, safe='')
url = f"https://developmenti.ipswich.qld.gov.au/Home/ApplicationDetailsView?appNo={encoded}&type=plan_development_apps"

print(f"Testing URL format:")
print(f"URL: {url}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    
    print(f"Page loaded")
    print(f"Title: {page.title()}")
    print(f"URL: {page.url}\n")
    
    # Check for divPrint (the modal container)
    div_print = page.locator("#divPrint")
    if div_print.count() > 0:
        print(f"✓ Found #divPrint!\n")
        
        # Extract fields
        fields = [
            ("Progress:", "h5:has-text('Progress:')"),
            ("Stage/Decision:", "h5:has-text('Stage/Decision:')"),
            ("Associated Properties", "h5:has-text('Associated Properties')"),
        ]
        
        for name, selector in fields:
            h5 = div_print.locator(selector)
            if h5.count() > 0:
                print(f"✓ Found: {name}")
                parent = h5.first.locator("xpath=..")
                # Get next div
                next_div = parent.locator("xpath=following-sibling::div").first
                if next_div and next_div.count() > 0:
                    text = next_div.text_content().strip()[:80]
                    print(f"  Value: {text}\n")
        
        # Check for property links
        prop_links = div_print.locator("a[href*='PropertyDetailsView']")
        print(f"Property links: {prop_links.count()}")
        for i in range(prop_links.count()):
            link = prop_links.nth(i)
            text = link.text_content().strip()
            href = link.get_attribute("href") or ""
            print(f"  {i+1}. {text}")
            print(f"     href: {href}")
    else:
        print(f"✗ No #divPrint found")
    
    browser.close()
