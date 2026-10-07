# PDF Failure Modes and Handling

## Purpose

Document processing fails in more ways than "OCR did not read a number." This solution makes those failure classes explicit and fails closed when correctness cannot be established.

## Usable text-layer decision

`usable_text_layer()` opens the document with `pdfplumber`, calls `extract_text()` page by page, removes whitespace, and counts remaining characters.

Default rule:

- at least 80 non-whitespace characters on a page; and
- at least 50% of pages must meet that threshold.

Diagnostics report per-page character counts, usable-page count, and page count.

This is a heuristic, not the extraction acceptance criterion. The supplied form is accepted primarily from its AcroForm values and then reconciled arithmetically.

## Failure matrix

| Failure | Detection | Baseline behavior | Production extension |
|---|---|---|---|
| missing path | filesystem check | `ExtractionError` | n/a |
| corrupt/truncated PDF | `PdfReader` exception | fail as unreadable/corrupt | quarantine + observability |
| encrypted PDF | reader encryption state / decryption | fail when empty-password access is unavailable | controlled password workflow |
| non-PDF upload | magic header | HTTP 400 | MIME + signature checks |
| oversized upload | byte limit | HTTP 413 | streaming limits/timeouts |
| AcroForm PDF | `get_fields()` | semantic field extraction | versioned field profiles |
| flattened text PDF | text layer exists but no supported fields | fail with explicit flattened-layout message | word/coordinate mapping |
| scanned/image-only PDF | text threshold fails | fail with OCR-required message | OCR pipeline |
| rotated/skewed scan | OCR preprocessing | optional | orientation + deskew |
| OCR punctuation errors | normalization + reconciliation | optional | confidence + review queue |
| wrong form revision | unsupported mapping / reconciliation | fail closed | version-specific layout registry |
| blank property columns | no values/address | omit property | n/a |
| duplicate/malformed fields | ambiguous mapping | fail unless unambiguous | revision-specific remediation |
| arithmetic mismatch | 2c/18/19 checks | reject extraction | manual review |
| DB persistence failure | SQLAlchemy exception | rollback + HTTP 500 | retry/telemetry |
| manual edit of totals | API category control | HTTP 400 | n/a |

## Scanned-PDF implementation design

The assignment makes OCR optional. If implemented, use:

```text
PDF page
  -> render at ~300 DPI
  -> orientation detection
  -> deskew / denoise if required
  -> Tesseract image_to_data()
  -> token text + bounding box + confidence
  -> normalize to form coordinates
  -> identify Form 8825 revision
  -> map tokens to row/column rectangles
  -> normalize money
  -> canonical property JSON
  -> same validate_property()
  -> confidence/arithmetic review gate
```

The important design property is that OCR only changes the acquisition layer. It does not change the accounting rules.

## OCR confidence policy

A production implementation should retain, for every extracted value:

- raw OCR text;
- normalized integer;
- confidence;
- page and bounding box;
- selected layout profile;
- validation result.

Low-confidence values or arithmetic mismatches must not be silently accepted.

## Version/revision mismatch

An AcroForm can be readable while still being unsafe to interpret with the wrong field map. `detect_profile()` therefore identifies known field signatures before line mapping. Unknown field structures raise `Unsupported Form 8825 AcroForm layout` instead of reusing the December 2025 mapping. Supporting a future revision requires an explicit profile and regression fixture.
