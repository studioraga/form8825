#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
.venv/bin/python -m pytest -q tests/test_api.py -k audit_captures_actor_request_and_client_identity
echo '=== P1.5 STRUCTURED AUDIT IDENTITY VALIDATION PASSED ==='
