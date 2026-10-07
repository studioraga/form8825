#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
source ~/.bashrc >/dev/null 2>&1 || true
cd frontend
npm ci
npm run build
npm run test:component
echo '=== P2.3 REACT COMPONENT/ACCESSIBILITY VALIDATION PASSED ==='
