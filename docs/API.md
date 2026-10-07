# API Contract and Validation

Base URL for local development: `http://127.0.0.1:8000`.

## Health

```http
GET /health
```

Expected:

```json
{"status":"ok"}
```

## Upload and extract

```http
POST /documents
Content-Type: multipart/form-data
```

Form field: `file`.

Controls:

- default maximum upload size: 20 MiB;
- body must start with `%PDF-`;
- extraction must pass Form 8825 arithmetic checks;
- persistence is transactional.

Successful response:

```json
{
  "document_id": 1,
  "properties": []
}
```

Representative errors:

- 400: not a PDF;
- 413: upload too large;
- 422: corrupt PDF, unsupported structure, scanned PDF without OCR, or arithmetic failure;
- 500: persistence failure.

## Retrieve a document

```http
GET /documents/{document_id}
```

Returns filename, SHA-256, extraction status, and persisted properties. Unknown IDs return 404.

## Correct a source line

```http
PATCH /properties/{property_id}/value
Content-Type: application/json
```

Example:

```json
{
  "category": "income_line_items",
  "key": "gross_rents",
  "value": 121000,
  "reason": "manual UI edit"
}
```

Only `income_line_items` and `expense_line_items` are editable. `totals` is rejected with HTTP 400. The backend recomputes total income, total expenses, and net income in the same transaction and marks them as `calculated`.

## Audit history

```http
GET /properties/{property_id}/audit
```

Returns ordered old/new-value records with reason and timestamp. Unknown properties return 404.

## Automated API validation

Backend tests cover:

- health;
- A/B/C upload;
- persisted document retrieval;
- income edit + recalculation + audit;
- expense edit + recalculation;
- totals edit rejected;
- unknown document/property/line rejected;
- non-PDF rejected;
- corrupt PDF rejected;
- upload-size limit.

`scripts/verify_api_db.sh` additionally exercises the live HTTP service with `curl` and verifies SQLite rows/provenance directly.

The live verifier includes an explicit startup-readiness gate. It polls `GET /health` quietly while Uvicorn starts, requires a successful health response before continuing, and fails closed if readiness is not reached within the bounded polling window. On readiness failure it prints the captured Uvicorn log and exits nonzero rather than attempting document/API validation against an unavailable service.

## Database startup prerequisite

The API assumes the database is already at the Alembic head revision. Deployment and verification must run `alembic upgrade head` before starting Uvicorn. This prevents hidden schema mutation during application import and makes database changes reviewable and reversible.
