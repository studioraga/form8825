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
