#!/usr/bin/env python3
"""Test property extraction by simulating enrichment flow."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT
import re

app_num = "14482/2025/MCU"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    # Go to MapSearch
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)
    
    # Search - try different search terms
    print(f"Testing different search terms for {app_num}:\n")
    
    for search_term in [app_num, "14482/2025", "14482", "MCU", "2025/MCU"]:
        print(f"Searching for: '{search_term}'")
        
        # Clear and search
        search_inputs = page.locator("input[type='text']")
        if search_inputs.count() > 0:
            search_input = search_inputs.first
            search_input.clear()
            search_input.fill(search_term)
            search_input.press("Enter")
            page.wait_for_timeout(2000)
            
            # Check if we found the Details button
            detail_button = page.locator(f"a[data-id='{app_num}'].application-moreinfo")
            print(f"  Details button found: {detail_button.count() > 0}")
            
            if detail_button.count() == 0:
                # Check how many results we got
                more_info_buttons = page.locator("a.application-moreinfo")
                print(f"  Total results shown: {more_info_buttons.count()}")
            print()
    
    browser.close()
