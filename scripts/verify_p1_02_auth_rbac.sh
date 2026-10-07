#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
export PYTHONPATH="$ROOT"
.venv/bin/python -m pytest -q tests/test_api.py -k rbac_api_key_roles
echo 'PASS: viewer/reviewer/admin API-key authorization semantics'
echo '=== P1.2 AUTH/RBAC VALIDATION PASSED ==='
