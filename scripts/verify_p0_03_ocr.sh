#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
command -v tesseract >/dev/null || { echo 'FAIL: tesseract missing'; exit 1; }
command -v pdftoppm >/dev/null || { echo 'FAIL: poppler/pdftoppm missing'; exit 1; }
export PYTHONPATH="$ROOT/src"
.venv/bin/python - <<'PY'
import importlib
for name in ('pytesseract','pdf2image'):
    importlib.import_module(name)
print('PASS: OCR Python dependencies')
PY
.venv/bin/python scripts/generate_scanned_fixture.py
SHA1=$(sha256sum data/f8825_multi_ABC_scanned.pdf | awk '{print $1}')
.venv/bin/python scripts/generate_scanned_fixture.py >/dev/null
SHA2=$(sha256sum data/f8825_multi_ABC_scanned.pdf | awk '{print $1}')
[[ "$SHA1" == "$SHA2" ]] || { echo 'FAIL: scanned fixture is not byte reproducible'; exit 1; }
echo "PASS: scanned fixture SHA-256 reproducible: $SHA1"
.venv/bin/python -m pytest -q tests/test_extraction.py -k 'scanned_fixture_ocr or scanned_fixture_is_reproducible'
.venv/bin/python - <<'PY'
import json
from form8825.extractor import extract_8825
actual=extract_8825('data/f8825_multi_ABC_scanned.pdf', allow_ocr=True)
expected=json.load(open('data/f8825_multi_ABC_expected.json'))
for got,want in zip(actual,expected):
    assert got['income_line_items']==want['income_line_items']
    assert got['expense_line_items']==want['expense_line_items']
    assert got['totals']==want['totals']
print('PASS: OCR financial values and arithmetic match expected A/B/C fixture')
PY
echo '=== P0.3 OCR VALIDATION PASSED ==='
