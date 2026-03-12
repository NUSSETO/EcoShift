import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './',
    testMatch: /.*\.spec\.js/,
    timeout: 30000,
    fullyParallel: false,
    retries: 0,
    use: {
        baseURL: 'http://localhost:5173',
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
            command: 'cd ../backend && DISABLE_BACKGROUND_REFRESH=1 uvicorn api.main:app --port 8000',
            port: 8000,
            timeout: 10000,
            reuseExistingServer: !process.env.CI,
        },
        {
            command: 'cd ../frontend && npm run dev',
            port: 5173,
            timeout: 10000,
            reuseExistingServer: !process.env.CI,
        }
    ],
});
