#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

"$ROOT/scripts/check_frontend_runtime.sh"

if [[ ! -f package-lock.json ]]; then
  echo "FAIL: package-lock.json is required for reproducible npm ci."
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "FAIL: root .venv is required because Playwright starts FastAPI with it."
  exit 1
fi

echo "=== npm ci ==="
npm ci

echo "=== production build ==="
npm run build

if [[ "${INSTALL_PLAYWRIGHT:-0}" == "1" ]]; then
  echo "=== installing Playwright Chromium ==="
  npx playwright install chromium
fi

echo "=== Playwright E2E ==="
npm run test:e2e

echo "=== FRONTEND/UI VALIDATION PASSED ==="
