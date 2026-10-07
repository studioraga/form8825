#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
export PYTHONPATH="$ROOT/src"
.venv/bin/python scripts/generate_multi_property_pdf.py >/dev/null
.venv/bin/python -m pytest -q tests/test_extraction.py -k 'flattened_multi_property_fixture or multi_property_matches_expected_json'
.venv/bin/python - <<'PY'
import json
from form8825.extractor import extract_8825
actual=extract_8825('data/f8825_multi_ABC_flattened.pdf')
expected=json.load(open('data/f8825_multi_ABC_expected.json'))
assert actual == expected
print('PASS: flattened coordinate extraction exact JSON')
PY
echo '=== P0.2 FLATTENED EXTRACTION VALIDATION PASSED ==='
