import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://developmenti.ipswich.qld.gov.au/Home/MapSearch');
});