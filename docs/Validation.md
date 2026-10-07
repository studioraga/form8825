# Validation and Verification Plan

This document is the authoritative gate for the GitHub baseline. Do not push the baseline commit until every required stage below passes.

## 1. Current status / preflight

From repository root:

```bash
pwd
python3 --version
node --version
npm --version
command -v nvm
nvm --version
```

Expected frontend runtime: Node >=20.19; the validated workstation setup uses Node 22 via `nvm`.

Validate repository content:

```bash
find . -maxdepth 3 -type f | sort
```

Do not commit `.venv`, `node_modules`, SQLite runtime databases, Vite `dist`, Playwright output, swap files, or pytest caches.

## 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip check
```

The exact baseline package versions are pinned in `requirements.txt` for reproducibility.

## 3. Frontend environment

```bash
source ~/.bashrc
cd frontend
nvm use
../scripts/check_frontend_runtime.sh
npm ci
cd ..
```

`.nvmrc` contains `22`. `package-lock.json` must be committed; clean validation uses `npm ci`.

## 4. Task 1 — supplied PDF extraction

```bash
source .venv/bin/activate
PYTHONPATH=src python -m form8825.extractor \
 data/f8825.pdf \
 -o artifacts/sample_generated.json
```

Expected: one property.

Exact JSON gate:

```bash
python - <<'PY'
import json
assert json.load(open('artifacts/sample_generated.json')) == json.load(open('data/8825_output.json'))
print('PASS: supplied PDF exact JSON')
PY
```

Expected key totals:

```text
Property A
line 2c = 1,734,896
line 18 = 1,246,695
line 19 = 488,201
```

## 5. Task 1 — text-layer decision

```bash
PYTHONPATH=src python - <<'PY'
from form8825.extractor import usable_text_layer
ok, diag = usable_text_layer('data/f8825.pdf')
print(ok, diag)
assert ok
PY
```

The extractor still prefers AcroForm values; the text probe is a classification/fallback diagnostic.

## 6. Task 1 — controlled failure tests

These are covered by `pytest`:

- missing file;
- corrupt PDF;
- image/blank PDF classified as lacking a usable text layer;
- money normalization;
- deliberate line 2c/18/19 mismatch detection.

## 7. Task 2 — regenerate A/B/C fixture

```bash
python scripts/generate_multi_property_pdf.py
```

Outputs:

```text
data/f8825_multi_ABC.pdf
data/f8825_multi_ABC_expected.json
```

Both derive from the same source data in the generator.

## 8. Task 2 — extract A/B/C

```bash
PYTHONPATH=src python -m form8825.extractor \
 data/f8825_multi_ABC.pdf \
 -o artifacts/multi_generated.json
```

Expected property order: `A`, `B`, `C`.

## 9. Task 2 — exact JSON gate

```bash
python - <<'PY'
import json
assert json.load(open('artifacts/multi_generated.json')) == json.load(open('data/f8825_multi_ABC_expected.json'))
print('PASS: A/B/C exact JSON')
PY
```

## 10. Task 2 — arithmetic gate

Expected:

| Property | Total income | Total expense | Net income |
|---|---:|---:|---:|
| A | 125000 | 89000 | 36000 |
| B | 212500 | 154200 | 58300 |
| C | 182500 | 122900 | 59600 |
| Grand net | | | 153900 |

`tests/test_extraction.py` asserts the known grand total `153900`, not merely an equivalent recomputation.

## 11. Python tests

```bash
pytest -q
```

Coverage includes extraction, failure handling, API behavior, arithmetic, persistence-facing responses, manual edit controls, audit, and upload limits.

## 12. Task 4 CSV evidence

```bash
PYTHONPATH=src python scripts/run_validation.py
column -s, -t artifacts/test_results.csv || cat artifacts/test_results.csv
```

CSV columns include UTC run time, PDF SHA-256, expected/actual totals, exact JSON result, arithmetic result, status, and failure reason.

Every row must be `PASS`.

### Validation artifact line endings

`artifacts/test_results.csv` is generated with explicit LF (`\n`) line
terminators. This keeps the committed validation evidence reproducible on
Linux and prevents carriage returns from being reported as trailing
whitespace by the Git pre-commit gate.

Repository `.gitattributes` also declares CSV/JSON/source files as LF text
and PDF fixtures as binary.

## 13. Backend one-shot verifier

```bash
./scripts/verify_backend.sh
```

This regenerates the fixture, extracts both documents, checks exact JSON, runs pytest, and emits CSV evidence.

## 14. Task 3 — API health

Manual mode:

```bash
source .venv/bin/activate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

From a second terminal:

```bash
curl -fsS http://127.0.0.1:8000/health | python -m json.tool
```

Expected: `{"status":"ok"}`.

## 15. Task 3 — upload A/B/C through the API

```bash
curl -fsS \
 -F 'file=@data/f8825_multi_ABC.pdf;type=application/pdf' \
 http://127.0.0.1:8000/documents | python -m json.tool
```

Expected: three properties.

## 16. Task 3 — retrieve persisted document

Use the returned `document_id`:

```bash
curl -fsS http://127.0.0.1:8000/documents/<DOCUMENT_ID> | python -m json.tool
```

Verify filename, SHA-256, completed status, and A/B/C data.

## 17. Task 3 — correct Property A

PATCH gross rents from `120000` to `121000`:

```bash
curl -fsS -X PATCH http://127.0.0.1:8000/properties/<PROPERTY_A_ID>/value \
 -H 'Content-Type: application/json' \
 -d '{"category":"income_line_items","key":"gross_rents","value":121000,"reason":"manual verification"}' \
 | python -m json.tool
```

Expected recalculated values:

```text
total income = 126000
total expense = 89000
net income = 37000
```

## 18. Task 3 — audit history

```bash
curl -fsS http://127.0.0.1:8000/properties/<PROPERTY_A_ID>/audit | python -m json.tool
```

Expected old/new values: `120000 -> 121000`.

## 19. Task 3 — totals cannot be directly edited

PATCHing category `totals` must return HTTP 400.

## 20. Task 3 — negative HTTP cases

Automated tests cover:

- unknown document/property/line -> 404;
- non-PDF -> 400;
- corrupt PDF -> 422;
- upload too large -> 413.

## 21. Task 3 — live API + DB verifier

```bash
./scripts/verify_api_db.sh
```

The script starts an isolated API against `artifacts/verify_api.db`, performs real HTTP calls, checks recalculated values/audit records, then queries SQLite directly for row counts and provenance.

### API readiness gate

The verifier does not assume that Uvicorn is ready immediately after the process is spawned. It polls `GET /health` for up to 50 attempts with a 0.2-second delay. Transient connection-refused probes are suppressed so expected startup races do not look like validation failures.

A separate `READY` flag is required before the verifier continues. If the service never becomes healthy, the script fails closed with:

```text
FAIL: API did not become ready on 127.0.0.1:8000
=== API server log ===
...
```

and prints `artifacts/verify_api_server.log` before exiting nonzero. Upload, correction, audit, DB, and negative-control checks are therefore executed only after an explicit health success.

## 22. Database inspection

Optional manual inspection:

```bash
python - <<'PY'
import sqlite3
con=sqlite3.connect('artifacts/verify_api.db')
for table in ['documents','properties','line_values','change_audit']:
 print('\n', table)
 for row in con.execute(f'SELECT * FROM {table}'):
 print(row)
con.close()
PY
```

## 23. React production build

```bash
source ~/.bashrc
cd frontend
nvm use
npm ci
npm run build
```

`vite build` must complete without error.

## 24. Playwright browser installation

One-time workstation setup:

```bash
npx playwright install chromium
```

The Node 22 setup must already be active.

## 25. UI behavior under test

Playwright verifies:

1. upload A/B/C;
2. render all three property cards;
3. verify Property A initial totals;
4. edit A gross rents on blur;
5. verify backend-recalculated totals;
6. display audit history;
7. reload browser and verify DB-backed persistence;
8. upload invalid content and verify controlled UI error.

## 26. Playwright execution

From `frontend/`:

```bash
npm run test:e2e
```

The Playwright configuration automatically starts:

- FastAPI on `127.0.0.1:8000` using the repository `.venv` and isolated `artifacts/e2e.db`;
- Vite on `127.0.0.1:5173`.

## 27. Frontend one-shot verifier

From repository root:

```bash
./scripts/verify_frontend.sh
```

For a workstation where Chromium is not installed yet:

```bash
INSTALL_PLAYWRIGHT=1 ./scripts/verify_frontend.sh
```

## 28. Full Task 1-4 verification

```bash
./scripts/verify_all.sh
```

Required final result:

```text
BACKEND VALIDATION PASSED
API/DB VALIDATION PASSED
FRONTEND/UI VALIDATION PASSED
ALL FORM 8825 TASK 1-4 VALIDATION PASSED
```

## 29. Git cleanliness gate

Before committing:

```bash
git status --short
git diff --check
find . -name '*.swp' -o -name '__pycache__' -o -name '.pytest_cache'
```

No runtime DB, `.venv`, `node_modules`, `dist`, test results directory, editor swap, or Python cache should be staged.

## 30. Inspect intended changes

```bash
git diff --stat
git diff -- requirements.txt .gitignore README.md

git diff -- docs scripts src api tests frontend
```

## 31. Stage baseline

```bash
git add \
 .gitignore README.md requirements.txt requirements-ocr.txt \
 docs data src api scripts tests frontend/package.json frontend/package-lock.json \
 frontend/.nvmrc frontend/index.html frontend/playwright.config.js \
 frontend/src frontend/tests
```

If you intentionally want generated validation evidence in Git, separately stage:

```bash
git add artifacts/sample_generated.json artifacts/multi_generated.json artifacts/test_results.csv
```

Do not stage `artifacts/*.db`.

## 32. Review staged content

```bash
git status
git diff --cached --stat
git diff --cached --check
```

## 33. Commit

Use the detailed commit message in `instruction.md`.

## 34. Post-commit verification

```bash
git status
git log -1 --stat --decorate
git show --check --stat HEAD
```

The working tree should be clean unless local validation evidence was intentionally regenerated after the commit.

## 35. Push

```bash
git remote -v
git branch --show-current
git push origin HEAD
```

Do not force-push unless the repository workflow explicitly requires it.

## 36-46. evidence sequence

For the , present evidence in this order:

36. show input and expected JSON;
37. show AcroForm-first extraction decision;
38. show text-layer diagnostics and scan fallback design;
39. run supplied-PDF extraction;
40. run A/B/C generator and extraction;
41. show exact JSON and line 2c/18/19 tests;
42. show CSV evidence and SHA-256;
43. show API upload/retrieve/edit/recalculation;
44. show SQLite provenance and audit history;
45. run React/Playwright E2E and demonstrate reload persistence;
46. run `./scripts/verify_all.sh`, then show clean Git status and the baseline commit.

This ordering matches the assignment rubric: AI/tool proficiency, code quality, extraction accuracy, data modeling, frontend implementation, and API design.

## P0.1 — Versioned profile verification

Run `./scripts/verify_p0_01_profiles.sh`. The gate proves that the supplied IRS form resolves to `irs-8825-2025-12`, the generated fixture resolves to `synthetic-8825-2025-12`, both still extract exactly, and an unknown AcroForm structure is rejected rather than interpreted with a stale map.

## P0.2 — Flattened coordinate extraction verification

Run `./scripts/verify_p0_02_flattened.sh`. It regenerates the flattened A/B/C fixture, extracts it through coordinate profiles, compares the result exactly with `f8825_multi_ABC_expected.json`, and proves that the existing AcroForm fixture still matches the same oracle.

## P0.3 — OCR verification

Run `./scripts/verify_p0_03_ocr.sh` after installing `requirements-ocr.txt`, Tesseract, and Poppler. The script generates an image-only scanned fixture from the deterministic flattened PDF, proves that the text-layer probe sees no native text, runs the OCR path, and compares every income, expense, and total value against the A/B/C expected JSON.

The scanned fixture generator also runs in ReportLab invariant mode after rasterization; the P0.3 verifier compares two generated SHA-256 values before OCR so the committed image-only evidence remains byte-reproducible.

## P1.1 — Alembic migration verification

Run `./scripts/verify_p1_01_migrations.sh`. It creates an isolated SQLite database, upgrades to head, checks the required tables plus `alembic_version`, downgrades to base, upgrades again, and prints the active revision. `verify_api_db.sh` also upgrades its isolated database before Uvicorn starts.

## P1.2 — Authentication/RBAC verification

Run `./scripts/verify_p1_02_auth_rbac.sh`. The test enables authentication, proves unauthenticated upload is 401, proves a viewer cannot upload (403), proves a reviewer can upload, and proves the viewer can subsequently read the persisted document.

## P1.3 — Optimistic concurrency verification

Run `./scripts/verify_p1_03_concurrency.sh`. The test uploads a document, performs one successful edit with the current version, confirms the version increments, then reuses the stale version for a second edit and requires HTTP 409.

## P1.4 — Duplicate/reprocessing verification

Run `./scripts/verify_p1_04_duplicates.sh`. The test uploads one fixture and verifies all three policies: `reuse` returns the original document ID, `reject` returns 409, and `reprocess` creates a new document linked to the first with generation 2.

## P1.5 — Structured audit identity verification

Run `./scripts/verify_p1_05_audit_identity.sh`. The test enables RBAC, authenticates a named reviewer, submits a correction with `X-Request-ID`, and requires the persisted audit row to contain the reviewer subject/role, correlation ID, and client IP.

## P2.1 — Background processing verification

Run `./scripts/verify_p2_01_background_jobs.sh`. The test submits the deterministic A/B/C fixture to `POST /jobs`, requires HTTP 202, polls the job record, verifies it reaches `completed` with a document ID, and then retrieves the persisted document.
