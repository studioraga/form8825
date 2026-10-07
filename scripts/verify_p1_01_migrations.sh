#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[[ -x .venv/bin/python ]] || { echo 'FAIL: .venv missing'; exit 1; }
DB="$ROOT/artifacts/migration_verify.db"; rm -f "$DB"; export DATABASE_URL="sqlite:///$DB"
.venv/bin/alembic upgrade head
.venv/bin/python - <<'PY'
import sqlite3
con=sqlite3.connect('artifacts/migration_verify.db')
tables={r[0] for r in con.execute("select name from sqlite_master where type='table'")}
required={'alembic_version','documents','properties','line_values','change_audit'}
assert required <= tables, (required,tables)
print('PASS: migration created expected schema')
con.close()
PY
.venv/bin/alembic downgrade base
.venv/bin/alembic upgrade head
.venv/bin/alembic current
.venv/bin/python - <<'PY2'
import sqlite3
con=sqlite3.connect('artifacts/migration_verify.db')
version=con.execute('select version_num from alembic_version').fetchone()
assert version and version[0], version
print('PASS: alembic_version persisted:', version[0])
con.close()
PY2
rm -f "$DB"
echo '=== P1.1 ALEMBIC MIGRATION VALIDATION PASSED ==='
