# Form 8825 AI-assisted extraction solution

End-to-end implementation for the four tasks: deterministic Form 8825 extraction, multi-property fixture generation, FastAPI/SQLite review workflow, React manual correction UI, and automated verification evidence.

## What is implemented

- **Task 1:** extract property income/expense values from the supplied December 2025 Form 8825 using open-source PDF libraries (`pypdf`, `pdfplumber`). The supplied file is AcroForm-backed, so semantic form fields are preferred over OCR.
- **Task 2:** generate a simulated A/B/C multi-property PDF and expected JSON from one source data structure, then extract and validate all three properties.
- **Task 3:** persist documents/properties/line values/audit history with FastAPI + SQLAlchemy + SQLite; review and correct source numbers in React; recalculate totals server-side.
- **Task 4:** verify exact JSON, line 2c/18/19 arithmetic, grand net income, API/DB controls, Vite build, and Playwright UI behavior; emit CSV evidence.

## Architecture

```text
PDF
 -> pypdf AcroForm extraction
 -> pdfplumber text-layer diagnostic/fallback classification
 -> canonical per-property JSON
 -> deterministic line 2c / 18 / 19 validation
 -> FastAPI
 -> SQLite provenance + audit
 -> React reviewer
 -> Playwright E2E
```

Detailed design: [`docs/Architecture.md`](docs/Architecture.md).

## Supplied sample expected values

Property A (`4th st plaza`):

```text
Total rental income (2c) = 1,734,896
Total expenses (18) = 1,246,695
Net income (19) = 488,201
```

## Synthetic A/B/C expected values

| Property | Total income | Total expense | Net income |
|---|---:|---:|---:|
| A | 125,000 | 89,000 | 36,000 |
| B | 212,500 | 154,200 | 58,300 |
| C | 182,500 | 122,900 | 59,600 |
| **Grand net** | | | **153,900** |

## Runtime baseline

Python dependencies are pinned in `requirements.txt`. Optional OCR dependencies are isolated in `requirements-ocr.txt`.

Frontend uses `.nvmrc` with Node 22 and a committed `package-lock.json`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

source ~/.bashrc
cd frontend
nvm use
npm ci
npx playwright install chromium
cd ..
```

## One-shot validation

Run each layer:

```bash
./scripts/verify_backend.sh
./scripts/verify_api_db.sh
./scripts/verify_frontend.sh
```

Then run the aggregate gate:

```bash
./scripts/verify_all.sh
```

Do not create the GitHub baseline commit until all stages pass.

The live API/DB verifier uses a bounded `/health` readiness gate. Expected connection-refused probes while Uvicorn is starting are suppressed; validation proceeds only after health succeeds. If readiness times out, the verifier prints the captured API server log and exits nonzero.

The detailed step-by-step sequence corresponding to the validation flow is in [`docs/Validation.md`](docs/Validation.md).

## PDF text layer and scan behavior

`usable_text_layer()` counts non-whitespace extractable text per page using `pdfplumber`; by default at least half the pages must contain at least 80 meaningful characters. This is a diagnostic classification, not a substitute for structured extraction.

The baseline fails closed when no supported AcroForm data exists:

- no usable text layer -> likely scanned/image-only input, OCR required;
- usable text but no supported fields -> flattened-layout coordinate extraction required.

OCR is optional for the assignment and is documented as a production extension in [`docs/PDF-Failure-Modes.md`](docs/PDF-Failure-Modes.md).

## API

- `GET /health`
- `POST /documents`
- `GET /documents/{id}`
- `PATCH /properties/{id}/value`
- `GET /properties/{id}/audit`

The API enforces upload limits, rejects non-PDF input, rejects direct edits of calculated totals, recalculates totals server-side, and records every manual source-value change.

See [`docs/API.md`](docs/API.md).

## Database model

- `documents`: file identity, SHA-256, status, timestamp;
- `properties`: per-document property identity/address;
- `line_values`: extracted/manual/calculated values and provenance;
- `change_audit`: append-only manual correction history through the API workflow.

SQLite foreign keys are enabled explicitly and uniqueness constraints prevent duplicate property/line identities.

See [`docs/Database.md`](docs/Database.md).

## Test coverage

Python tests cover:

- supplied PDF exact JSON;
- A/B/C exact JSON;
- known grand total `153900`;
- line 2c/18/19 validation;
- text-layer diagnostics;
- money normalization;
- missing/corrupt/image-only failure paths;
- API health/upload/retrieve;
- income and expense recalculation;
- immutable calculated-total policy;
- audit history;
- 404/400/413/422 cases.

Playwright covers:

- upload A/B/C;
- initial displayed values;
- manual Property A correction;
- server recalculation;
- audit display;
- persistence across browser reload;
- controlled invalid-PDF UI error.

`scripts/run_validation.py` emits `artifacts/test_results.csv` with UTC timestamp, source PDF SHA-256, expected/actual totals, exact JSON result, arithmetic result, status, and failure reason.

## Documentation

- [`docs/instruction.md`](docs/instruction.md) — setup, validation baseline, staging, commit, push
- [`docs/Architecture.md`](docs/Architecture.md) — end-to-end design
- [`docs/Validation.md`](docs/Validation.md) — authoritative Task 1-4 verification sequence
- [`docs/API.md`](docs/API.md) — API contract and tests
- [`docs/Database.md`](docs/Database.md) — schema/provenance/audit model
- [`docs/PDF-Failure-Modes.md`](docs/PDF-Failure-Modes.md) — PDF/OCR failure handling
- [`docs/Walkthrough.md`](docs/Walkthrough.md) — 20-minute presentation plan
- [`docs/Review.md`](docs/Review.md) — source review, hardening changes, and validation status

## GitHub baseline

After all verifiers pass, follow `docs/instruction.md`. It contains the complete staging sequence and recommended detailed commit message.

AI is presented as an implementation accelerator, not the correctness oracle. The acceptance evidence is deterministic: structured extraction, exact expected data, arithmetic invariants, negative tests, transaction/audit controls, reproducible dependencies, and end-to-end automation.
