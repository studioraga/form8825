# Form 8825 Solution Architecture

## 1. Scope

This repository implements the four tasks around IRS Form 8825:

1. extract property income/expense values from the supplied PDF;
2. generate and validate a deterministic multi-property A/B/C fixture;
3. persist extraction results behind FastAPI/SQLite and review/edit them from React;
4. verify JSON correctness, line 2c/18/19 arithmetic, grand-total net income, API/database behavior, and UI behavior.

The architecture is intentionally deterministic. AI may accelerate implementation and test design, but extraction acceptance is controlled by explicit field mappings, exact expected JSON, arithmetic invariants, database provenance, and automated tests.

## 2. End-to-end architecture

```text
 +-------------------------+
 | Form 8825 PDF |
 +------------+------------+
 |
 +------------v------------+
 | PDF preflight / parsing |
 | pypdf + pdfplumber |
 +------------+------------+
 |
 +---------------------+---------------------+
 | |
 +---------v----------+ +---------v----------+
 | AcroForm values | | text-layer probe |
 | preferred path | | usable / unusable |
 +---------+----------+ +---------+----------+
 | |
 | no fields|
 | v
 | +-------------------+
 | | flattened / scan |
 | | OCR extension |
 | +-------------------+
 v
 +--------------------+
 | canonical property |
 | JSON representation|
 +---------+----------+
 |
 +---------v----------+
 | deterministic |
 | arithmetic checks |
 | 2c, 18, 19 |
 +---------+----------+
 |
 +---------v----------+
 | FastAPI service |
 +---------+----------+
 |
 +-------+-------+
 | |
+-------v------+ +------v-------+
| SQLite DB | | React review |
| provenance | | and editing |
| + audit | +------+-------+
+------+------+ |
 ^ |
 +---------------+
 PATCH + server
 recalculation
```

## 3. Extraction hierarchy

### 3.1 AcroForm first

The supplied December 2025 Form 8825 contains AcroForm values. `pypdf.PdfReader.get_fields()` is therefore the highest-confidence extraction path. Values are mapped to a canonical schema instead of reconstructing the visual table with OCR.

Supported field layouts:

- the supplied IRS page-1 A-D field pattern (`Line2a`, `Line18`, etc. plus adjacent numeric field identifiers);
- the synthetic fixture's canonical names, for example `property.A.line2a`.

### 3.2 Text-layer probe

`usable_text_layer()` uses `pdfplumber`, removes whitespace, and counts extractable text per page. A PDF is considered text-usable when at least 50% of pages contain at least 80 non-whitespace characters. This reduces false positives from image PDFs that contain only tiny hidden text fragments.

### 3.3 Flattened text and scanned input

The baseline intentionally fails closed if a PDF has no supported AcroForm structure. If substantial text exists, the error identifies the missing flattened-coordinate implementation. If substantial text does not exist, the error identifies likely scanned/image-only input.

The optional scanned path is documented in `PDF-Failure-Modes.md` and uses page rendering + OCR + bounding boxes + confidence + version-specific cell geometry before feeding the same canonical validation layer.

## 4. Canonical property schema

```json
{
 "property_name": "A",
 "property_address": "...",
 "income_line_items": {
 "gross_rents": 0,
 "other_income": 0
 },
 "expense_line_items": {
 "advertising": 0,
 "auto_travel": 0,
 "cleaning_maintenance": 0,
 "commissions": 0,
 "insurance": 0,
 "interest": 0,
 "legal_professional": 0,
 "real_estate_taxes": 0,
 "repairs": 0,
 "utilities": 0,
 "wages_salaries": 0,
 "depreciation": 0,
 "other_deductions": 0
 },
 "totals": {
 "total_rental_income": 0,
 "total_expenses": 0,
 "net_income": 0
 }
}
```

Money is represented as whole-dollar integers to avoid floating-point accounting drift.

## 5. Arithmetic invariants

For every property:

```text
line 2c = line 2a + line 2b
line 18 = sum(expense line items 3-17 represented by the schema)
line 19 = line 2c - line 18
```

For the multi-property fixture:

```text
Grand total net income = sum(property line 19 values)
 = 153,900
```

Extraction fails if a populated PDF does not reconcile.

## 6. Synthetic A/B/C fixture

`scripts/generate_multi_property_pdf.py` defines one source data structure and derives both:

- `data/f8825_multi_ABC.pdf`
- `data/f8825_multi_ABC_expected.json`

This prevents fixture drift caused by separately hand-maintaining a PDF and expected output.

Expected totals:

| Property | line 2c | line 18 | line 19 |
|---|---:|---:|---:|
| A | 125,000 | 89,000 | 36,000 |
| B | 212,500 | 154,200 | 58,300 |
| C | 182,500 | 122,900 | 59,600 |
| Grand net | | | 153,900 |

## 7. API architecture

The API exposes:

- `GET /health`
- `POST /documents`
- `GET /documents/{document_id}`
- `PATCH /properties/{property_id}/value`
- `GET /properties/{property_id}/audit`

Key controls:

- live verification is gated on bounded `GET /health` readiness before API/DB assertions run;
- upload-size limit (`MAX_UPLOAD_BYTES`, default 20 MiB);
- `%PDF-` magic-header check;
- extraction failures returned as HTTP 422;
- totals cannot be manually patched;
- totals are recalculated server-side after source-value edits;
- every source-value edit creates an audit record;
- SQLAlchemy transactions roll back on persistence errors;
- CORS is limited to the local Vite origins used by the demo.

See `API.md`.

## 8. Database architecture

```text
documents 1 ---- * properties 1 ---- * line_values
 |
 +------------- * change_audit
```

`line_values.source` records provenance (`extracted`, `manual`, `calculated`). Database uniqueness constraints prevent duplicate properties per document and duplicate line keys per property/category. SQLite foreign-key enforcement is explicitly enabled.

See `Database.md`.

## 9. React architecture

The React UI:

- uploads a PDF;
- renders A/B/C property cards;
- edits source line values only;
- saves on blur/Enter rather than issuing PATCH requests on every keystroke;
- renders server-recalculated totals with stable test IDs;
- displays audit history;
- stores the last document ID in local storage and reloads it via `GET /documents/{id}` after a browser refresh.

This makes persistence observable in the E2E test.

## 10. Validation architecture

Validation is layered:

```text
static/runtime preflight
 |
fixture regeneration
 |
extract real + synthetic PDFs
 |
exact JSON comparison
 |
pytest extraction/API/negative tests
 |
CSV evidence generation
 |
API + SQLite verification script
 |
Vite production build
 |
Playwright end-to-end UI test
```

Use `scripts/verify_all.sh` for the final gate. Detailed commands and expected results are in `Validation.md`.
