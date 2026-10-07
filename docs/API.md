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

## Authentication and RBAC

Set `AUTH_MODE=enabled` and configure `FORM8825_API_KEYS` as comma-separated `key:role:subject` entries. Roles are hierarchical: `viewer` can read documents/audit history, `reviewer` can also upload and correct source values, and `admin` is reserved for full administrative access. Missing/invalid keys return HTTP 401; insufficient roles return HTTP 403. The local demo remains backward-compatible with `AUTH_MODE=disabled`. The React client can send a key through `VITE_API_KEY`.

## Optimistic concurrency

Each property carries a monotonically increasing `version`. `PATCH /properties/{property_id}/value` requires `expected_version`; stale edits receive HTTP 409 instead of silently overwriting a newer reviewer change. A successful edit increments the property version and returns the new version with the recalculated values.

## Duplicate and reprocessing policy

`POST /documents` computes SHA-256 before extraction and applies `DUPLICATE_DOCUMENT_POLICY`: `reuse` returns the newest existing document for the hash, `reject` returns HTTP 409, and `reprocess` creates a new document linked to the previous record. Responses expose `duplicate_action` so callers can distinguish `created`, `reused`, and `reprocessed` outcomes.

## Structured audit identity

Every accepted manual correction records the authenticated subject and role, a request correlation ID, and the observed client IP in addition to old/new values and reason. Callers may supply `X-Request-ID`; otherwise the API generates one. Audit retrieval returns these identity fields so a correction can be traced back to an actor and request context.

## Background processing API

`POST /jobs` accepts the same PDF upload but returns HTTP 202 with a job ID. The FastAPI background worker updates `processing_jobs` through `queued`, `running`, `completed`, or `failed`, and stores the resulting `document_id` or error text. `GET /jobs/{job_id}` exposes job state. The synchronous `POST /documents` path remains available for small/demo documents.

## Observability

All HTTP requests pass through correlation/metrics middleware. `X-Request-ID` is preserved when supplied or generated when absent, returned on the response, and reused by audit logging. Structured JSON request logs include request ID, method, path, status, and duration. `GET /metrics` exposes Prometheus-compatible counters for request volume, response status, and cumulative latency; production deployments should restrict the metrics endpoint at the network/proxy layer.

## Front-end accessibility interaction contract

API errors surfaced by the React client are rendered with `role="alert"`, upload progress uses an `aria-live` region, and server validation remains authoritative. The API itself is unchanged by accessibility support; UI tests verify that backend failures are exposed through accessible status semantics.

## OpenAPI contract snapshot

The runtime OpenAPI document is exported deterministically to [`openapi.json`](openapi.json). Contract tests compare the committed snapshot with `app.openapi()` and assert that required routes, API-key security, and the optimistic-concurrency request field remain present. Any API shape change must intentionally regenerate and review the snapshot.
