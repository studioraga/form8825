from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader

from .profiles import FORM_8825_2025_12, FormProfile, detect_profile

PROPERTY_NAMES = ["A", "B", "C", "D"]
INCOME_KEYS = {"2a": "gross_rents", "2b": "other_income"}
EXPENSE_KEYS = {
    "3": "advertising",
    "4": "auto_travel",
    "5": "cleaning_maintenance",
    "6": "commissions",
    "7": "insurance",
    "8": "interest",
    "9": "legal_professional",
    "10": "real_estate_taxes",
    "11": "repairs",
    "12": "utilities",
    "13": "wages_salaries",
    "14": "depreciation",
    "17": "other_deductions",
}
TOTAL_KEYS = {"2c": "total_rental_income", "18": "total_expenses", "19": "net_income"}

IRS_LINE_BASE = FORM_8825_2025_12.line_base


class ExtractionError(RuntimeError):
    pass


def parse_money(value: Any) -> int:
    if value is None:
        return 0
    s = str(value).strip()
    if not s:
        return 0
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {"-", "."}:
        return 0
    n = int(round(float(s)))
    return -abs(n) if negative else n


def usable_text_layer(pdf_path: str | Path, min_chars: int = 80, min_ratio: float = 0.5) -> tuple[bool, dict[str, Any]]:
    """A page is text-usable when extractable non-whitespace text is substantial.

    We require at least `min_chars` on at least `min_ratio` of pages. This avoids
    treating a scanned PDF with only a tiny OCR/header layer as text-native.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            counts = [len(re.sub(r"\s+", "", page.extract_text() or "")) for page in pdf.pages]
    except Exception as exc:
        return False, {"reason": f"text_probe_failed: {exc}", "page_char_counts": []}
    if not counts:
        return False, {"reason": "no_pages", "page_char_counts": []}
    usable_pages = sum(c >= min_chars for c in counts)
    ok = usable_pages / len(counts) >= min_ratio
    return ok, {"page_char_counts": counts, "usable_pages": usable_pages, "page_count": len(counts)}


def _empty_property(name: str, address: str = "") -> dict[str, Any]:
    return {
        "property_name": name,
        "property_address": address,
        "income_line_items": {k: 0 for k in INCOME_KEYS.values()},
        "expense_line_items": {k: 0 for k in EXPENSE_KEYS.values()},
        "totals": {k: 0 for k in TOTAL_KEYS.values()},
    }


def _field_value(v: dict[str, Any]) -> Any:
    return v.get("/V") if isinstance(v, dict) else None


def _parse_canonical_fields(fields: dict[str, Any]) -> list[dict[str, Any]]:
    props: dict[str, dict[str, Any]] = {}
    rx = re.compile(r"^property\.([A-D])\.(address|line(?:2a|2b|2c|[3-9]|1[0-9]))$")
    for key, meta in fields.items():
        m = rx.match(key)
        if not m:
            continue
        p, item = m.groups()
        props.setdefault(p, _empty_property(p))
        val = _field_value(meta)
        if item == "address":
            props[p]["property_address"] = str(val or "").strip()
            continue
        line = item.removeprefix("line")
        if line in INCOME_KEYS:
            props[p]["income_line_items"][INCOME_KEYS[line]] = parse_money(val)
        elif line in EXPENSE_KEYS:
            props[p]["expense_line_items"][EXPENSE_KEYS[line]] = parse_money(val)
        elif line in TOTAL_KEYS:
            props[p]["totals"][TOTAL_KEYS[line]] = parse_money(val)
    return [props[p] for p in PROPERTY_NAMES if p in props and (props[p]["property_address"] or any(props[p]["totals"].values()) or any(props[p]["income_line_items"].values()) or any(props[p]["expense_line_items"].values()))]


def _property_from_irs_field(line: str, field_name: str, known_addresses: list[str], profile: FormProfile) -> str:
    m = re.search(r"\.f1_(\d+)\[", field_name)
    if m and line in profile.line_base:
        num = int(m.group(1))
        base = profile.line_base[line]
        if base <= num <= base + 3:
            return PROPERTY_NAMES[num - base]
    # Some real-world PDFs have malformed/reused numeric suffixes. If only A is
    # populated, the semantic LineXX path remains reliable and A is unambiguous.
    if len(known_addresses) == 1:
        return "A"
    raise ExtractionError(f"Cannot determine property column for field {field_name}")


def _parse_irs_acroform(fields: dict[str, Any], profile: FormProfile = FORM_8825_2025_12) -> list[dict[str, Any]]:
    props = {p: _empty_property(p) for p in PROPERTY_NAMES}
    populated_addresses: list[str] = []

    # Address fields: RowA/RowB/... when available; otherwise infer from f1_3..22.
    for key, meta in fields.items():
        val = str(_field_value(meta) or "").strip()
        if not val or "Table_Line1" not in key or ".Col_a" not in key:
            continue
        m = re.search(r"\.Row([A-D])\[", key)
        if m:
            p = m.group(1)
        else:
            n = re.search(r"\.f1_(\d+)\[", key)
            if not n:
                continue
            idx = (int(n.group(1)) - 3) // 5
            if idx not in range(4):
                continue
            p = PROPERTY_NAMES[idx]
        props[p]["property_address"] = val
        populated_addresses.append(p)

    line_rx = re.compile(r"\.Line(2a|2b|2c|[3-9]|1[0-9])\[")
    for key, meta in fields.items():
        m = line_rx.search(key)
        if not m:
            continue
        line = m.group(1)
        val = _field_value(meta)
        if val in (None, ""):
            continue
        p = _property_from_irs_field(line, key, populated_addresses, profile)
        if line in INCOME_KEYS:
            props[p]["income_line_items"][INCOME_KEYS[line]] = parse_money(val)
        elif line in EXPENSE_KEYS:
            props[p]["expense_line_items"][EXPENSE_KEYS[line]] = parse_money(val)
        elif line in TOTAL_KEYS:
            props[p]["totals"][TOTAL_KEYS[line]] = parse_money(val)

    return [props[p] for p in PROPERTY_NAMES if props[p]["property_address"] or any(props[p]["totals"].values()) or any(props[p]["income_line_items"].values()) or any(props[p]["expense_line_items"].values())]


def validate_property(prop: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    inc = prop["income_line_items"]
    exp = prop["expense_line_items"]
    totals = prop["totals"]
    calc_income = inc["gross_rents"] + inc["other_income"]
    calc_expense = sum(exp.values())
    calc_net = calc_income - calc_expense
    if totals["total_rental_income"] != calc_income:
        errors.append(f"line2c expected {calc_income}, got {totals['total_rental_income']}")
    if totals["total_expenses"] != calc_expense:
        errors.append(f"line18 expected {calc_expense}, got {totals['total_expenses']}")
    if totals["net_income"] != calc_net:
        errors.append(f"line19 expected {calc_net}, got {totals['net_income']}")
    return errors


def extract_8825(pdf_path: str | Path, *, validate: bool = True, allow_ocr: bool = False) -> list[dict[str, Any]]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise ExtractionError(f"PDF not found: {pdf_path}")
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ExtractionError("Encrypted PDF requires a password") from exc
        fields = reader.get_fields() or {}
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Unreadable/corrupt PDF: {exc}") from exc

    profile = detect_profile(fields) if fields else None
    if fields and profile is None:
        raise ExtractionError(
            "Unsupported Form 8825 AcroForm layout. Add a versioned profile and regression fixture "
            "before accepting this field structure."
        )

    props = _parse_canonical_fields(fields) if profile and profile.profile_id.startswith("synthetic-") else []
    if not props and profile:
        props = _parse_irs_acroform(fields, profile)

    if not props:
        usable, diagnostics = usable_text_layer(pdf_path)
        if not usable:
            if allow_ocr:
                raise ExtractionError(
                    "No usable text/form layer. OCR hook requested, but OCR is optional in this submission; "
                    "install Tesseract + pdf2image and route OCR words through the same coordinate mapping. "
                    f"Diagnostics: {diagnostics}"
                )
            raise ExtractionError(
                "No usable AcroForm values and no usable text layer. Likely scanned/image-only input. "
                f"Diagnostics: {diagnostics}"
            )
        raise ExtractionError(
            "Text layer exists but no supported Form 8825 field structure was found. "
            "For flattened text PDFs, add coordinate/word-table mapping for the form revision."
        )

    if validate:
        all_errors = {p["property_name"]: validate_property(p) for p in props}
        all_errors = {k: v for k, v in all_errors.items() if v}
        if all_errors:
            raise ExtractionError(f"Arithmetic validation failed: {all_errors}")
    return props


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract property income/expenses from IRS Form 8825 PDF")
    ap.add_argument("pdf")
    ap.add_argument("-o", "--output", default="8825_output.generated.json")
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--allow-ocr", action="store_true")
    args = ap.parse_args()
    result = extract_8825(args.pdf, validate=not args.no_validate, allow_ocr=args.allow_ocr)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(result)} properties)")

if __name__ == "__main__":
    main()
