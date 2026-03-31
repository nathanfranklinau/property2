#!/usr/bin/env python3
"""Inspect the actual property link structure in the modal."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

app_num = sys.argv[1] if len(sys.argv) > 1 else "14482/2025/MCU"

print(f"\nInspecting property links for: {app_num}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(user_agent=USER_AGENT)
    
    # Go to search page
    print("1. Loading search page...")
    page.goto("https://developmenti.ipswich.qld.gov.au/Home/MapSearch")
    page.wait_for_timeout(3000)
    
    # Search
    print(f"2. Searching for {app_num}...")
    search_inputs = page.locator("input[type='text']")
    for i in range(search_inputs.count()):
        placeholder = (search_inputs.nth(i).get_attribute("placeholder") or "").lower()
        if "search" in placeholder or "application" in placeholder:
            search_inputs.nth(i).fill(app_num)
            search_inputs.nth(i).press("Enter")
            break
    
    page.wait_for_timeout(3000)
    
    # Click Details button
    print("3. Clicking Details button...")
    detail_button = page.locator(f"a[data-id='{app_num}'].application-moreinfo")
    if detail_button.count() > 0:
        detail_button.first.click()
        page.wait_for_timeout(2000)
        
        # Check modal
        modal = page.locator("#divPrint")
        if modal.count() > 0:
            print("✓ Modal appeared\n")
            
            # Look for Associated Properties section
            props_section = modal.locator("h5:has-text('Associated Properties')")
            if props_section.count() > 0:
                print("✓ Found 'Associated Properties' section")
                
                # Get parent and siblings
                parent = props_section.first.locator("xpath=..")
                following_divs = parent.locator("xpath=following-sibling::*")
                print(f"  Following siblings: {following_divs.count()}")
                
                # Get the HTML of the properties section
                section_html = parent.evaluate("el => el.outerHTML")
                print(f"\nHTML of Associated Properties section:")
                print(section_html[:500])
                print("...\n")
                
                # Look for all links near the properties section
                all_links = modal.locator("a")
                print(f"All links in modal: {all_links.count()}")
                for i in range(all_links.count()):
                    link = all_links.nth(i)
                    href = link.get_attribute("href") or ""
                    text = link.text_content().strip()[:60]
                    if "Adelong" in text or "landNumber" in href or "THAGOONA" in text:
                        print(f"  PROPERTY LINK: href='{href}'")
                        print(f"               text='{text}'")
                        print(f"               class='{link.get_attribute('class')}'")
                        print()
            else:
                print("✗ No 'Associated Properties' section found")
                
                # Try other selectors
                all_h5 = modal.locator("h5")
                print(f"\nAll h5 headings in modal:")
                for i in range(all_h5.count()):
                    text = all_h5.nth(i).text_content().strip()
                    print(f"  {i}. {text}")
        else:
            print("✗ Modal did not appear")
    else:
        print(f"✗ No Details button found")
    
    browser.close()
