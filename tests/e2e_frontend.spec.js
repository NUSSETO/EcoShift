import { test, expect } from '@playwright/test';

test.describe('EcoShift Dashboard E2E', () => {
    test('loads dashboard with chart and proper line overlays', async ({ page }) => {
        // Navigate to the Vite dev server
        await page.goto('http://localhost:3000/');

        // 1. Verify that the Dashboard loads — check for the chart title
        await expect(page.locator('h2', { hasText: 'Energy Draw' })).toBeVisible({ timeout: 15000 });

        // 2. Verify header elements
        await expect(page.locator('.header-brand h2', { hasText: 'EcoShift' })).toBeVisible();
        await expect(page.locator('.status-indicator')).toBeVisible();

        // 3. If a critical alert is present, verify it renders in the header
        const headerAlert = page.locator('.header-alert-card').first();
        const alertVisible = await headerAlert.isVisible().catch(() => false);
        if (alertVisible) {
            await expect(headerAlert).toHaveClass(/critical|warning/);
            // Verify it contains type, message, and time elements
            await expect(headerAlert.locator('.header-alert-type')).toBeVisible();
            await expect(headerAlert.locator('.header-alert-message')).toBeVisible();
            await expect(headerAlert.locator('.header-alert-time')).toBeVisible();
        }

        // 4. Verify Charting Library Overlay (solid actual vs dashed predicted)
        // Recharts renders lines as SVG <path> elements with the class 'recharts-line-curve'
        const lines = page.locator('path.recharts-line-curve');

        // We expect at least two visible lines (actual + predicted; hoverTracker is transparent)
        const lineCount = await lines.count();
        expect(lineCount).toBeGreaterThanOrEqual(2);

        // 5. Verify time range controls exist
        await expect(page.locator('button', { hasText: '24H' })).toBeVisible();
        await expect(page.locator('button', { hasText: '7 Days' })).toBeVisible();
        await expect(page.locator('button', { hasText: 'MTD' })).toBeVisible();

        // 6. Verify metric toggle
        await expect(page.locator('button', { hasText: 'Energy Draw' })).toBeVisible();
        await expect(page.locator('button', { hasText: 'Carbon Emissions' })).toBeVisible();
    });
});
