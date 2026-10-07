#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo "FAIL: create .venv first"; exit 1; }
export PYTHONPATH="$ROOT/src"
.venv/bin/python -m pytest -q tests/test_extraction.py -k 'profile or sample_matches or multi_property_matches'
.venv/bin/python - <<'PY'
from pathlib import Path
from pypdf import PdfReader
from form8825.profiles import detect_profile
root=Path('.')
for name in ('f8825.pdf','f8825_multi_ABC.pdf'):
    profile=detect_profile(PdfReader(str(root/'data'/name)).get_fields() or {})
    assert profile is not None
    print(f'PASS: {name} -> {profile.profile_id}')
PY
echo '=== P0.1 VERSIONED PROFILE VALIDATION PASSED ==='
