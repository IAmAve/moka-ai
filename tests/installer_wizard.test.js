// Playwright test for installer wizard accessibility
const { test, expect } = require('@playwright/test');

// Resolve absolute path to index.html
const path = require('path');
const indexPath = 'file://' + path.resolve(__dirname, '../installer_wizard/index.html');

test('keyboard navigation and focus management', async ({ page }) => {
  await page.goto(indexPath);
  // Fill a valid install path to enable Get Started
  const input = page.locator('#install-path');
  await input.fill('C:/Program Files/Moka AI');
  // Tab to Get Started button
  await page.keyboard.press('Tab'); // to Browse button
  await page.keyboard.press('Tab'); // to Get Started button
  // Press Enter to activate Get Started
  await page.keyboard.press('Enter');
  // Wait for step 2 to be active
  await expect(page.locator('#step-2')).toHaveClass(/active/);
  // Verify focus moved to primary button of step 2 (Continue)
  const focused = await page.evaluate(() => document.activeElement.id);
  expect(focused).toBe('btn-continue-hw');
});
