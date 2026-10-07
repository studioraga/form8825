#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
.venv/bin/python -m pytest -q tests/test_api.py -k optimistic_concurrency_rejects_stale_edit
echo '=== P1.3 OPTIMISTIC CONCURRENCY VALIDATION PASSED ==='
