# Source Review and Baseline Changes

## Reviewed source

Baseline input reviewed: `form8825-current.tar.gz`.

The review covered:

- `src/form8825/extractor.py`
- `api/db.py`
- `api/main.py`
- Python tests
- multi-property fixture generator
- CSV validation script
- React application
- Playwright configuration/test
- Python/npm dependency definitions
- repository ignore/runtime artifacts
- README and missing documentation.

## What was already working

The attached implementation already had the essential end-to-end shape:

- supplied PDF AcroForm extraction;
- text-layer probe;
- deterministic canonical JSON;
- A/B/C synthetic fixture;
- arithmetic validation;
- FastAPI + SQLite persistence;
- manual-edit audit data;
- React property display/editing;
- Playwright smoke test;
- CSV validation evidence.

The earlier execution evidence showed the supplied and synthetic extraction paths passing and identified Node 18 as the frontend runtime blocker. Node/nvm was subsequently corrected by the user to Node 22.

## Baseline hardening performed in this revision

### Python / extraction

- removed the eager extractor import from `form8825/__init__.py`, preventing the `python -m form8825.extractor` runpy double-import warning;
- expanded extraction tests for money parsing, deliberate arithmetic corruption, missing PDFs, corrupt PDFs, and image/blank PDFs;
- changed the grand-total test to assert the known value `153900` explicitly;
- made the synthetic PDF byte-reproducible with ReportLab `invariant=1` and added a repeated-SHA-256 regression test.

### API

- added `/health`;
- hardened the live API verifier with bounded health polling, an explicit readiness flag, quiet transient startup probes, and fail-closed server-log output;
- added a configurable upload limit (`MAX_UPLOAD_BYTES`, default 20 MiB);
- retained PDF magic-header validation;
- added explicit property existence checks;
- added transaction rollback handling;
- retained server-only recalculation of totals;
- added negative API coverage for non-PDF, corrupt PDF, missing entities, invalid line keys, immutable totals, and upload limits.

### Database

- enabled SQLite foreign-key enforcement;
- added uniqueness constraints for property identity and line-value identity;
- added explicit audit relationship/cascades;
- retained source provenance (`extracted`, `manual`, `calculated`).

### React

- stopped issuing PATCH requests on every keystroke; edits now save on blur/Enter;
- added controlled UI error display;
- added stable total test IDs;
- added audit-history display;
- reloads the most recently uploaded document through the backend after browser refresh.

### Playwright

The E2E workflow now verifies:

- A/B/C display;
- Property A initial totals;
- gross-rent correction;
- recalculated income/expense/net values;
- audit history;
- persistence across reload;
- invalid-PDF UI error.

Playwright starts FastAPI using the repository `.venv` and an isolated SQLite E2E DB.

### Dependencies

- Python dependencies are pinned in `requirements.txt` to the versions observed in the successful workstation installation;
- optional OCR dependencies are separated into `requirements-ocr.txt`;
- frontend dependencies are pinned rather than `latest`;
- `.nvmrc` remains Node 22;
- `package-lock.json` is retained for `npm ci` reproducibility.

### Verification

Added:

- `scripts/check_frontend_runtime.sh`
- `scripts/verify_backend.sh`
- `scripts/verify_api_db.sh`
- `scripts/verify_frontend.sh`
- `scripts/verify_all.sh`

CSV evidence now includes run timestamp, source PDF SHA-256, failure reason, and expected/actual totals.

### Documentation

Added/expanded:

- `docs/instruction.md`
- `docs/Architecture.md`
- `docs/Validation.md`
- `docs/API.md`
- `docs/Database.md`
- `docs/PDF-Failure-Modes.md`
- `docs/Walkthrough.md`
- `docs/Review.md`

## Validation performed during review

In the review environment:

- Python test suite after fixture-reproducibility coverage: **18 passed**;
- supplied PDF extraction: exact expected JSON passed;
- A/B/C extraction: exact expected JSON passed;
- CSV validation: all rows passed;
- known A/B/C grand total: `153900` passed.
- added `.gitattributes` so generated PDF fixtures are treated as binary and
  source/evidence text is normalized to LF;
- changed CSV evidence generation to explicit LF line endings so
  `git diff --cached --check` remains clean.

The user's Node 22 workstation subsequently validated the Vite production build, both Playwright end-to-end tests, the live API/SQLite verification, and the aggregate Task 1-4 gate. After the later readiness/reproducibility hardening, the complete aggregate verifier must be rerun once more before the Git baseline commit so that the final commit matches the exact validated source.

## Remaining production extensions (not required by the assignment)

- actual scanned-PDF OCR implementation;
- flattened text-coordinate profile for Form 8825 revisions;
- Alembic migrations;
- authentication/authorization and reviewer identity in audit records;
- structured logging/metrics;
- malware/content scanning for uploads;
- durable object/file storage rather than temporary upload bytes;
- browser UI for reason entry and richer audit filtering.

### P0.1 — Versioned layout profiles

The extractor no longer assumes every AcroForm is the December 2025 layout. Structural profile detection selects the real/synthetic mappings and unknown AcroForms fail closed. This converts form-revision support into an explicit registry plus regression-test contract.

### P0.2 — Flattened coordinate extraction

The former flattened-PDF failure path now has a real profile-driven implementation. A generated flattened A/B/C fixture is parsed through `pdfplumber` cell crops and compared against the same expected JSON used by the AcroForm fixture, while unknown layouts remain fail-closed.
