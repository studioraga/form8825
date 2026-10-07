# Implementation, Validation, and GitHub Baseline Instructions

## Goal

Treat this repository as the candidate baseline only after the complete Task 1-4 verification in `Validation.md` passes on the workstation.

## Fresh setup

```bash
cd ~/dev/pub/ai-sys1/USbank/form8825

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip check
```

Frontend runtime:

```bash
source ~/.bashrc
cd frontend
nvm use
node --version
npm --version
npm ci
npx playwright install chromium
cd ..
```

The validated local convention is `.nvmrc = 22`; `package.json` rejects unsupported Node releases with its engine declaration.

## Required verification

Run the layers independently first:

```bash
./scripts/verify_backend.sh
./scripts/verify_api_db.sh
./scripts/verify_frontend.sh
```

Then run the aggregate gate:

```bash
./scripts/verify_all.sh
```

Do not create the Git baseline commit if any stage fails.

`verify_api_db.sh` has a bounded API-readiness gate: startup probe errors are suppressed during the polling window, but the script requires a successful `/health` response before any upload/update/database checks. If readiness never succeeds, it prints the captured API server log and exits nonzero.

## Evidence files

Regenerated validation evidence:

```text
artifacts/sample_generated.json
artifacts/multi_generated.json
artifacts/test_results.csv
```

Runtime-only files such as `artifacts/*.db`, `frontend/dist`, Playwright output, `.venv`, and `node_modules` are ignored and should not be committed.

## Git preflight

If this directory is already a Git repository:

```bash
git status --short
git branch --show-current
git remote -v
git log --oneline --decorate -5
```

If it is not yet a Git repository, initialize only if that is the intended workflow:

```bash
git init
```

Do not overwrite or reconstruct existing history when a `.git` directory exists in your real working copy.

## Stage after validation

```bash
git add \
 .gitignore README.md requirements.txt requirements-ocr.txt \
 docs data src api scripts tests \
 frontend/.nvmrc frontend/index.html frontend/package.json frontend/package-lock.json \
 frontend/playwright.config.js frontend/src frontend/tests
```

Optional evidence staging:

```bash
git add artifacts/sample_generated.json artifacts/multi_generated.json artifacts/test_results.csv
```

Review:

```bash
git status
git diff --cached --stat
git diff --cached --check
```
Before committing, `git diff --cached --check` must return no output.
`.gitattributes` marks PDF fixtures as binary and normalizes committed text
and CSV evidence to LF. Do not bypass this check.

## Recommended commit message

```text
feat: establish auditable Form 8825 extraction and review baseline

Implement the end-to-end Form 8825 document-processing solution for
single- and multi-property rental real-estate income/expense review.

Extraction and validation:
- prefer AcroForm field extraction for the supplied IRS Form 8825
- preserve a text-layer diagnostic for flattened/scanned-PDF routing
- normalize monetary values into a canonical per-property JSON schema
- fail closed when line 2c, line 18, or line 19 does not reconcile
- generate byte-reproducible A/B/C PDF and expected JSON from one source
- assert the known multi-property grand net income of 153,900
- add negative tests for missing, corrupt, and image/blank PDFs
- regression-test byte reproducibility of the generated A/B/C PDF

API and persistence:
- add FastAPI health, upload, retrieve, correction, and audit endpoints
- enforce PDF signature and configurable upload-size limits
- reject manual edits to calculated totals
- recalculate totals server-side after source-value corrections
- add transaction rollback handling and explicit HTTP failures
- persist SHA-256, extraction status, value provenance, and audit history
- add SQLite foreign-key enforcement and uniqueness constraints
- gate live API/DB verification on bounded health readiness and print server logs on startup failure

React and UI automation:
- pin Node/npm dependency versions and retain the Node 22 nvm contract
- save financial edits on blur/Enter instead of every keystroke
- expose stable total-value test IDs and reviewer audit history
- reload the last persisted document from the backend
- extend Playwright coverage for A/B/C display, recalculation, audit,
 persistence across reload, and invalid-PDF handling

Verification and documentation:
- pin Python baseline dependencies and document optional OCR extras
- add backend, live API/DB, frontend, and aggregate verification scripts
- enrich CSV validation evidence with source SHA-256 and timestamps
- add architecture, validation, API, DB, PDF-failure, and docs
- expand .gitignore for runtime, test, editor, frontend, and transient live-API artifacts

Validated gate:
- supplied PDF exact JSON and arithmetic checks
- A/B/C exact JSON, per-property totals, and grand net income
- pytest extraction/API negative and positive cases
- live HTTP + SQLite provenance/audit verification with readiness gating
- Vite production build and Playwright end-to-end UI workflow
```

Commit:

```bash
git commit -s -F /tmp/form8825-commit-message.txt
```

One convenient way to use the message is to copy the text above into `/tmp/form8825-commit-message.txt` first. If your repository does not require Developer Certificate of Origin sign-off, omit `-s`.

## Push

```bash
git status
git log -1 --stat --decorate
git remote -v
git push origin HEAD
```
Keep the final terminal evidence for the full verifier PASS, `git status`, and `git log -1 --stat`.

## P0.1 validation — versioned Form 8825 profiles

Before accepting another IRS revision, add a `FormProfile` in `src/form8825/profiles.py`, add a revision-specific fixture/test, and run `./scripts/verify_p0_01_profiles.sh`. Do not reuse the December 2025 field map for an unrecognized form signature.

## P0.2 validation — flattened PDFs

Calibrate a new flattened form by adding a versioned `FlatLayoutProfile` with measured cell boxes and a representative fixture. Run `./scripts/verify_p0_02_flattened.sh` before enabling the profile. Never infer arbitrary table geometry from a filename alone.
