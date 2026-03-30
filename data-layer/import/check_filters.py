#!/usr/bin/env python3
"""Check what filter controls exist in the filter panel."""

from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)
    
    # Show the filter panel if it's hidden
    filters = page.locator("#search-filters")
    if filters.count() > 0:
        # Force it visible
        page.evaluate("document.getElementById('search-filters').style.display = 'block'")
        page.wait_for_timeout(500)
        
        # Get all form labels and inputs
        labels = filters.locator("label")
        print(f"Filter labels ({labels.count()}):")
        for i in range(labels.count()):
            text = labels.nth(i).text_content().strip()
            print(f"  {text}")
        
        print(f"\nFilter selects/inputs:")
        selects = filters.locator("select")
        for i in range(selects.count()):
            id_attr = selects.nth(i).get_attribute("id") or ""
            name_attr = selects.nth(i).get_attribute("name") or ""
            options = selects.nth(i).locator("option")
            print(f"  {id_attr} (name={name_attr}): {options.count()} options")
        
        inputs = filters.locator("input[type='text']")
        print(f"\nText inputs: {inputs.count()}")
    
    browser.close()
