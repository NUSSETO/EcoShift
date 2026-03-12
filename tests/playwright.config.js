import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './',
    testMatch: /.*\.spec\.js/,
    timeout: 30000,
    fullyParallel: false,
    retries: 0,
    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: [
        {
            command: 'cd ../backend && uvicorn api.main:app --port 8000',
            port: 8000,
            timeout: 15000,
            reuseExistingServer: !process.env.CI,
        },
        {
            command: 'cd ../frontend && npm run dev -- --port 3000',
            port: 3000,
            timeout: 15000,
            reuseExistingServer: !process.env.CI,
        }
    ],
});
