import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'rm -f artifacts/e2e.db && DATABASE_URL=sqlite:///./artifacts/e2e.db .venv/bin/alembic upgrade head && DATABASE_URL=sqlite:///./artifacts/e2e.db DUPLICATE_DOCUMENT_POLICY=reprocess .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      cwd: '..',
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
