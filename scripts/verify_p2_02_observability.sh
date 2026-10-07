#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
.venv/bin/python -m pytest -q tests/test_api.py -k observability_request_id_and_metrics
echo '=== P2.2 OBSERVABILITY VALIDATION PASSED ==='
