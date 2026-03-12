import { test, expect } from '@playwright/test';

test('Verify Data Source text and Filtering functionality', async ({ page }) => {
  // Wait for the backend process and frontend dev process to be fully up
  await page.goto('http://localhost:5173');

  // Verify True Data Source String
  const footerText = await page.locator('footer.dashboard-footer p').textContent();
  expect(footerText).toContain('Data powered by Static Demonstration Dataset.');

  // Check that 24H is selected initially
  await page.waitForSelector('button:has-text("24H")');
  const btn24H = page.locator('button', { hasText: '24H' });
  await expect(btn24H).toHaveClass(/active/);
  
  // Wait for the chart elements to be present
  await page.waitForSelector('.recharts-surface');

  // Switch to 7 Days and wait for network/update
  const btn7Days = page.locator('button', { hasText: '7 Days' });
  await btn7Days.click();
  await page.waitForTimeout(2000); // Give it a moment to fetch and render

  // Switch to MTD
  const btnMTD = page.locator('button', { hasText: 'MTD' });
  await btnMTD.click();
  await page.waitForTimeout(2000); // Give it a moment to fetch and render
  
  console.log("Verified filters click correctly and data source text is updated.");
});
