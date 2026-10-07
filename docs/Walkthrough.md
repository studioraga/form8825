# 20-Minute Walkthrough

## 0-2 minutes — requirement and trust model

Show the supplied Form 8825 and expected JSON. State the acceptance invariants:

- line 2c = 2a + 2b;
- line 18 = sum of expense items;
- line 19 = line 2c - line 18;
- grand net = sum of property net incomes.

Explain that AI accelerated implementation/iteration, while deterministic mappings, known-answer fixtures, arithmetic checks, tests, and audit records establish correctness.

## 2-5 minutes — PDF strategy

Show `src/form8825/extractor.py`.

Explain:

1. AcroForm first for the supplied PDF;
2. text-layer diagnostic using `pdfplumber`;
3. explicit failure for flattened or scanned PDFs not implemented by the baseline;
4. OCR production extension keeps bounding boxes/confidence and feeds the same canonical validator.

## 5-8 minutes — Task 1

Run:

```bash
PYTHONPATH=src python -m form8825.extractor data/f8825.pdf -o artifacts/sample_generated.json
```

Compare with expected JSON and show Property A totals.

## 8-11 minutes — Task 2

Run generator and A/B/C extraction. Explain that PDF and expected JSON come from one source data structure. Show the known values and grand net `153900`.

## 11-14 minutes — Task 4 deterministic tests

Run:

```bash
pytest -q
PYTHONPATH=src python scripts/run_validation.py
```

Show negative PDF tests and the CSV evidence containing source hashes and expected/actual totals.

## 14-17 minutes — Task 3 API/DB

Run:

```bash
./scripts/verify_api_db.sh
```

Show upload, Property A correction, server-side recalculation, audit history, and SQLite provenance (`manual` source input and `calculated` totals).

## 17-19 minutes — React/UI automation

Run:

```bash
./scripts/verify_frontend.sh
```

Explain the edit-on-blur behavior, totals test IDs, audit display, local-storage document pointer, backend reload, and Playwright invalid-PDF test.

## 19-20 minutes — production extensions

Mention:

- versioned IRS form-layout profiles;
- scanned-PDF OCR with confidence and coordinate mapping;
- password workflow for encrypted PDFs;
- stricter resource/time limits;
- migrations (Alembic) instead of `create_all`;
- authentication/authorization for real reviewer edits;
- structured logs/metrics;
- human review queue for low-confidence fields.

Finish with:

```bash
./scripts/verify_all.sh
git status
git log -1 --stat
```

### Enhancement: versioned Form 8825 profiles

For production evolution, point to `src/form8825/profiles.py`: the field map is revision-scoped, detected by structural signatures, and unsupported revisions are rejected. This is the first control to discuss when asked how the solution handles future IRS form changes.

### Enhancement: flattened text support

Show `src/form8825/flattened.py` and explain that flattened documents are accepted only when a revision-specific coordinate profile is recognized. The same expected JSON and arithmetic checks validate both AcroForm and flattened extraction, avoiding a second business-logic path.

### Enhancement: scanned-PDF OCR

Demonstrate the distinction between native text and OCR: `usable_text_layer()` fails for the image-only fixture, `allow_ocr=True` activates Tesseract/Poppler, and the recovered financial values are still accepted only after the existing arithmetic invariants pass. Call out OCR confidence and address review as the next production control.

### Enhancement: production schema evolution

When discussing operational readiness, show the Alembic migration chain and explain why schema changes are no longer side effects of importing FastAPI. Deployment upgrades the database first, then starts the service; tests separately prove downgrade and re-upgrade behavior.

### Enhancement: authentication and role separation

Show that React is not the security boundary. FastAPI enforces viewer versus reviewer permissions even for direct callers. Mention that the environment-backed API-key adapter is intentionally replaceable by enterprise OIDC/JWT without changing the financial data model.

### Enhancement: concurrent reviewer safety

Demonstrate one accepted correction followed by a stale retry. The second request is rejected with 409, showing that concurrent review conflicts are surfaced instead of silently losing another user's change.

### Enhancement: duplicate and reprocessing semantics

Use SHA-256 lineage to explain idempotency versus intentional reruns. A repeated upload can reuse, reject, or create generation 2 linked to generation 1; the behavior is configuration, not an accidental side effect.

### Enhancement: attributable corrections

When showing the audit endpoint, point out that the record now answers who changed the value, which role authorized it, which request performed it, and where it originated—not only the numeric delta.

### Enhancement: asynchronous processing

Contrast `POST /documents` with `POST /jobs`: the former is convenient for the small exercise, while the latter returns 202 and exposes durable status. Explain that the job table/API is the stable contract and FastAPI BackgroundTasks is only the current executor.

### Enhancement: observability and correlation

Show one request carrying `X-Request-ID`, then the response header, structured request log, metrics counter, and audit `request_id`. This demonstrates one correlation key across operations and financial evidence.
