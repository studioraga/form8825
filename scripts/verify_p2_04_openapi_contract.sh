#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
.venv/bin/python -m pip check >/dev/null || { echo 'FAIL: Python dependency check failed'; exit 1; }
.venv/bin/python - <<'PY'
from importlib.metadata import version
expected = {
    'fastapi': '0.142.2',
    'pydantic': '2.13.5',
    'starlette': '1.7.0',
    'python-multipart': '0.0.32',
}
for package, wanted in expected.items():
    actual = version(package)
    if actual != wanted:
        raise SystemExit(f'FAIL: {package} version {actual} != pinned {wanted}')
    print(f'PASS: {package}=={actual}')
PY
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
PYTHONPATH=. .venv/bin/python - <<'PY' > "$TMP"
import json
from api.main import app
print(json.dumps(app.openapi(), indent=2, sort_keys=True))
PY
cmp -s "$TMP" docs/openapi.json || { echo 'FAIL: docs/openapi.json drifted from runtime OpenAPI'; diff -u docs/openapi.json "$TMP" | head -120; exit 1; }
.venv/bin/python -m pytest -q tests/test_openapi_contract.py
echo '=== P2.4 OPENAPI CONTRACT VALIDATION PASSED ==='
