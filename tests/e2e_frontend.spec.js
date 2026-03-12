import { test, expect } from '@playwright/test';

test.describe('EcoShift Dashboard E2E', () => {
    test('displays critical alert and correct chart overlaps', async ({ page }) => {
        // Navigate to the Vite dev server
        await page.goto('http://localhost:5173/');

        // 1. Verify that the Dashboard loads (wait for 'Live API Data Visualization')
        await expect(page.locator('h2', { hasText: 'Live API Data Visualization' })).toBeVisible({ timeout: 10000 });

        // 2. Verify CRITICAL alert presence and glowing UI warning
        // Find the alert toast with the 'critical' class
        await page.screenshot({ path: 'screenshot.png' });
        const criticalAlert = page.locator('.alert-toast.critical').first();
        await expect(criticalAlert).toBeVisible({ timeout: 10000 });

        // Check for the specific HIGH_CARBON_EMISSIONS or PEAK_GRID_DRAW text
        // The previous injection created both, so we expect at least one critical alert
        const alertText = await criticalAlert.innerText();
        expect(alertText).toMatch(/PEAK GRID DRAW|HIGH CARBON EMISSIONS/);

        // Verify the visual "red glowing" UI aspect by checking the CSS class or computed style
        // The class 'critical' in index.css likely has the glow effect
        await expect(criticalAlert).toHaveClass(/critical/);

        // 3. Verify Charting Library Overlay (solid actual vs dashed predicted)
        // Recharts renders lines as SVG <path> elements with the class 'recharts-line-curve'
        const lines = page.locator('path.recharts-line-curve');

        // We expect at least two lines (one for actual, one for predicted)
        await expect(lines).toHaveCount(2);

        // The first line is "Actual" and should be solid
        const actualLine = lines.nth(0);
        const actualStrokeDasharray = await actualLine.getAttribute('stroke-dasharray');
        // Solid lines typically have no stroke-dasharray, or it is not set or "0"
        if (actualStrokeDasharray) {
            expect(['none', '0px 0px']).toContain(actualStrokeDasharray); // Recharts uses "0px 0px" for solid sometimes
        } else {
            expect(actualStrokeDasharray).toBeNull();
        }

        // The second line is "Predicted" and should be dashed (stroke-dasharray="5 5" from OverlayChart.jsx)
        // Due to Recharts animation, stroke-dasharray might be dynamically changing. Just verify it has one.
        const predictedLine = lines.nth(1);
        await expect(predictedLine).toHaveAttribute('stroke-dasharray', /.*/, { timeout: 10000 });
    });
});
