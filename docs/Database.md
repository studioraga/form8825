# Database Model and Audit Design

## Tables

### `documents`

- `id`
- `filename`
- `sha256`
- `extraction_status`
- `created_at`

The SHA-256 identifies the exact uploaded bytes used for extraction.

### `properties`

- `id`
- `document_id`
- `property_name`
- `property_address`

Constraint: one property name per document.

### `line_values`

- `id`
- `property_id`
- `category`
- `key`
- `value`
- `source`

Constraint: one `(property_id, category, key)` value.

Provenance values used by the application:

- `extracted` — initially read from the PDF;
- `manual` — source value changed by the reviewer;
- `calculated` — total recalculated by the backend.

### `change_audit`

- `id`
- `property_id`
- `category`
- `key`
- `old_value`
- `new_value`
- `reason`
- `changed_at`

Audit rows are append-only through the normal API workflow.

## Relationships

```text
documents
  1
  |
  * properties
       1
       +------ * line_values
       |
       +------ * change_audit
```

`ON DELETE CASCADE` and ORM cascades keep dependent data consistent. SQLite foreign-key enforcement is explicitly turned on at connection time.

## Verification

Run:

```bash
./scripts/verify_api_db.sh
```

The script verifies:

- exactly one uploaded document;
- exactly three A/B/C properties;
- one audit record after the scripted correction;
- Property A net income stored as `37000` with source `calculated`.

## Alembic migration contract

Production/deployment schema changes are versioned under `migrations/versions/`. Initialize or upgrade a database with `alembic upgrade head`; inspect with `alembic current`; rollback testing may use `alembic downgrade`. Application startup does not call `create_all()`. Any later model change must include a forward/backward migration and migration-verification coverage.

## Authentication storage boundary

The current RBAC implementation intentionally reads API-key principals from environment configuration and does not store credentials in SQLite. This keeps the exercise dependency-light and avoids persisting secrets in the application database. A production identity provider would replace this adapter; financial document/audit tables remain independent of authentication credential storage.

## Property versioning

`properties.version` is an integer concurrency token introduced by Alembic revision `0002`. It starts at 1 and increments after each accepted source-value correction. API callers must submit the version they observed; stale versions are rejected before any line value or audit row is changed.

## Document reprocessing lineage

Alembic revision `0003` adds `documents.reprocessed_from_id` and `processing_generation`. A reprocessed document points to the previous stored document with the same SHA-256 and increments its generation. SHA-256 remains indexed but is intentionally not unique because controlled reprocessing is allowed.

## Audit identity fields

Alembic revision `0004` adds `actor_id`, `actor_role`, `request_id`, and `client_ip` to `change_audit`. Together with property/category/key, old/new values, reason, and timestamp, the row now captures who changed what, why, and through which request context.

## Processing jobs

Alembic revision `0005` adds `processing_jobs` with filename, SHA-256, status, resulting `document_id`, error text, and timestamps. Job records survive beyond the HTTP request and provide a durable status surface for asynchronous processing. The current implementation uses FastAPI background tasks; a production worker queue can replace the executor while preserving the table/API contract.

## Observability and persistence correlation

No new observability table is required for the baseline. Request correlation is carried in `change_audit.request_id`, while runtime counters/logs remain operational telemetry rather than business records. This avoids mixing short-lived metrics with durable financial audit data.
