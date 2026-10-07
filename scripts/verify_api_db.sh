#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "FAIL: .venv missing."
  exit 1
fi

mkdir -p artifacts
DB="$ROOT/artifacts/verify_api.db"
LOG="$ROOT/artifacts/verify_api_server.log"
UPLOAD_JSON="$ROOT/artifacts/verify_api_upload.json"
PATCH_JSON="$ROOT/artifacts/verify_api_patch.json"
AUDIT_JSON="$ROOT/artifacts/verify_api_audit.json"
rm -f "$DB" "$LOG" "$UPLOAD_JSON" "$PATCH_JSON" "$AUDIT_JSON"

export DATABASE_URL="sqlite:///$DB"
export MAX_UPLOAD_BYTES=$((20*1024*1024))

.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 >"$LOG" 2>&1 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

READY=0
for _ in $(seq 1 50); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" != "1" ]]; then
  echo "FAIL: API did not become ready on 127.0.0.1:8000"
  echo "=== API server log ==="
  cat "$LOG" || true
  exit 1
fi

curl -fsS http://127.0.0.1:8000/health | .venv/bin/python -m json.tool

echo "=== Upload A/B/C ==="
curl -fsS -F 'file=@data/f8825_multi_ABC.pdf;type=application/pdf' http://127.0.0.1:8000/documents > "$UPLOAD_JSON"
.venv/bin/python -m json.tool "$UPLOAD_JSON"

read -r DOC_ID PROP_A <<<"$(.venv/bin/python - <<'PY'
import json
x=json.load(open('artifacts/verify_api_upload.json'))
assert [p['property_name'] for p in x['properties']] == ['A','B','C']
a=x['properties'][0]
assert a['totals'] == {'total_rental_income':125000,'total_expenses':89000,'net_income':36000}
print(x['document_id'], a['id'])
PY
)"

echo "=== GET persisted document ==="
curl -fsS "http://127.0.0.1:8000/documents/$DOC_ID" | .venv/bin/python -m json.tool >/dev/null

echo "=== PATCH A gross rents 120000 -> 121000 ==="
curl -fsS -X PATCH "http://127.0.0.1:8000/properties/$PROP_A/value" \
  -H 'Content-Type: application/json' \
  -d '{"category":"income_line_items","key":"gross_rents","value":121000,"reason":"verification script"}' > "$PATCH_JSON"
.venv/bin/python - <<'PY'
import json
x=json.load(open('artifacts/verify_api_patch.json'))
assert x['income_line_items']['gross_rents']==121000
assert x['totals']['total_rental_income']==126000
assert x['totals']['total_expenses']==89000
assert x['totals']['net_income']==37000
print('PASS: API recalculation')
PY

echo "=== Audit ==="
curl -fsS "http://127.0.0.1:8000/properties/$PROP_A/audit" > "$AUDIT_JSON"
.venv/bin/python - <<'PY'
import json
x=json.load(open('artifacts/verify_api_audit.json'))
assert x[-1]['key']=='gross_rents'
assert x[-1]['old_value']==120000
assert x[-1]['new_value']==121000
assert x[-1]['reason']=='verification script'
print('PASS: audit trail')
PY

echo "=== DB rows ==="
.venv/bin/python - <<'PY'
import sqlite3
con=sqlite3.connect('artifacts/verify_api.db')
assert con.execute('select count(*) from documents').fetchone()[0] == 1
assert con.execute('select count(*) from properties').fetchone()[0] == 3
assert con.execute('select count(*) from change_audit').fetchone()[0] == 1
row=con.execute("select value,source from line_values where property_id=(select id from properties where property_name='A') and category='totals' and key='net_income'").fetchone()
assert row == (37000,'calculated'), row
print('PASS: DB persistence/provenance')
con.close()
PY

echo "=== Negative API controls ==="
STATUS=$(curl -sS -o /dev/null -w '%{http_code}' -X PATCH "http://127.0.0.1:8000/properties/$PROP_A/value" \
  -H 'Content-Type: application/json' -d '{"category":"totals","key":"net_income","value":999999}')
[[ "$STATUS" == "400" ]] || { echo "FAIL: expected 400 editing totals, got $STATUS"; exit 1; }
STATUS=$(curl -sS -o /dev/null -w '%{http_code}' -F 'file=@requirements.txt;type=application/pdf' http://127.0.0.1:8000/documents)
[[ "$STATUS" == "400" ]] || { echo "FAIL: expected 400 non-PDF, got $STATUS"; exit 1; }

echo "=== API/DB VALIDATION PASSED ==="
