import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  // Recording...
  await page.goto('https://developmenti.ipswich.qld.gov.au/Home/MapSearch');
  await page.waitForTimeout(1000);
  await page.locator('h2.mobile-filters').click();
  await page.waitForTimeout(1000);
  await page.locator('#filter-status-type').selectOption('all');
  await page.waitForTimeout(1000);

  await page.locator('#show-daterange').click();
  await page.waitForTimeout(1000);

  await page.locator('#date-range-dropdown input[name="status"][value="submitted"]').check();
  await page.waitForTimeout(1000);

  await page.locator('#dateRangeInput').click();
  await page.waitForTimeout(1000);

  await page.locator('input[name="daterangepicker_start"]').click();
  await page.locator('input[name="daterangepicker_start"]').fill('01/01/2020');
  await page.waitForTimeout(1000);

  await page.locator('input[name="daterangepicker_end"]').click();
  await page.locator('input[name="daterangepicker_end"]').fill('01/06/2020');
  await page.waitForTimeout(1000);

  await page.locator('.daterangepicker button.applyBtn').click();
  await page.waitForTimeout(1000);

  await page.locator('h2.mobile-filters').click();
  await page.waitForTimeout(1000);

  const downloadPromise = page.waitForEvent('download');
  await page.locator('.download-csv .fa.fa-download').click();
  const download = await downloadPromise;
  await page.waitForTimeout(2000);

});