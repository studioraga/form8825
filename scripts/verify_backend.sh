#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "FAIL: .venv missing. Create it and install requirements.txt first."
  exit 1
fi

source .venv/bin/activate
mkdir -p artifacts

echo "=== [1/7] Python runtime ==="
python --version
python -m pip --version

echo "=== [2/7] Re-generate deterministic A/B/C fixture ==="
python scripts/generate_multi_property_pdf.py

echo "=== [3/7] Extract supplied Form 8825 ==="
PYTHONPATH=src python -m form8825.extractor data/f8825.pdf -o artifacts/sample_generated.json

echo "=== [4/7] Extract A/B/C fixture ==="
PYTHONPATH=src python -m form8825.extractor data/f8825_multi_ABC.pdf -o artifacts/multi_generated.json

echo "=== [5/7] Exact JSON comparison ==="
python - <<'PY'
import json
from pathlib import Path
pairs=[
 ('sample', Path('data/8825_output.json'), Path('artifacts/sample_generated.json')),
 ('multi_ABC', Path('data/f8825_multi_ABC_expected.json'), Path('artifacts/multi_generated.json')),
]
for name, expected_path, actual_path in pairs:
    expected=json.loads(expected_path.read_text())
    actual=json.loads(actual_path.read_text())
    assert actual == expected, f'{name}: exact JSON mismatch'
    print(f'PASS: {name} exact JSON')
PY

echo "=== [6/7] pytest ==="
pytest -q

echo "=== [7/7] CSV validation evidence ==="
PYTHONPATH=src python scripts/run_validation.py

echo "=== BACKEND VALIDATION PASSED ==="
