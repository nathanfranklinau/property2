#!/usr/bin/env python3
"""Inspect modal for an application to check if property links exist."""

import sys
from playwright.sync_api import sync_playwright
from da_common import USER_AGENT

app_num = sys.argv[1] if len(sys.argv) > 1 else "10157/2018/MAPDA/A"

print(f"\nInspecting modal for: {app_num}\n")

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
            
            # Check for property links
            prop_links = modal.locator("a[href*='PropertyDetailsView?landNumber=']")
            print(f"Property links with 'PropertyDetailsView?landNumber=': {prop_links.count()}")
            
            # Check for any a tags with land number in href
            all_links = modal.locator("a[href*='landNumber']")
            print(f"All links with 'landNumber': {all_links.count()}")
            
            # Show all links in the modal
            all_a_tags = modal.locator("a")
            print(f"Total links in modal: {all_a_tags.count()}\n")
            
            print("All links in modal:")
            for i in range(min(10, all_a_tags.count())):
                link = all_a_tags.nth(i)
                href = link.get_attribute("href") or ""
                text = link.text_content().strip()[:60]
                print(f"  {i}. href='{href}' text='{text}'")
            
            # Get the full HTML to inspect structure
            modal_html = modal.evaluate("el => el.innerHTML")
            
            # Look for "Property" or "Land" mentions
            if "Property" in modal_html or "property" in modal_html or "Land" in modal_html:
                print(f"\n✓ Modal mentions 'Property' or 'Land'")
            else:
                print(f"\n✗ Modal does NOT mention 'Property' or 'Land'")
            
            # Save HTML for inspection
            with open("/tmp/modal_inspect.html", "w") as f:
                f.write(f"<html><body>{modal_html}</body></html>")
            print("\n✓ Saved modal HTML to /tmp/modal_inspect.html")
        else:
            print("✗ Modal did not appear")
    else:
        print(f"✗ No Details button found for {app_num}")
    
    browser.close()
    print("\n✓ Done - browser closed")
