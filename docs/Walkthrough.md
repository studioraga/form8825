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
