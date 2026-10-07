from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from form8825.extractor import (  # noqa: E402
    ExtractionError,
    extract_8825,
    parse_money,
    usable_text_layer,
    validate_property,
)


def test_sample_matches_expected_json():
    actual = extract_8825(ROOT / "data/f8825.pdf")
    expected = json.loads((ROOT / "data/8825_output.json").read_text())
    assert actual == expected


def test_multi_property_matches_expected_json():
    actual = extract_8825(ROOT / "data/f8825_multi_ABC.pdf")
    expected = json.loads((ROOT / "data/f8825_multi_ABC_expected.json").read_text())
    assert actual == expected
    assert [p["property_name"] for p in actual] == ["A", "B", "C"]


def test_arithmetic_and_known_grand_total():
    actual = extract_8825(ROOT / "data/f8825_multi_ABC.pdf")
    assert all(validate_property(p) == [] for p in actual)
    assert sum(p["totals"]["net_income"] for p in actual) == 153_900
    assert sum(p["totals"]["net_income"] for p in actual) == sum(
        p["totals"]["total_rental_income"] - p["totals"]["total_expenses"]
        for p in actual
    )


def test_sample_has_usable_text_layer():
    ok, diag = usable_text_layer(ROOT / "data/f8825.pdf")
    assert ok, diag
    assert diag["page_count"] == 2


def test_money_normalization():
    assert parse_money("1,234") == 1234
    assert parse_money("$2,345") == 2345
    assert parse_money("(500)") == -500
    assert parse_money(0) == 0
    assert parse_money("") == 0


def test_validation_detects_all_three_total_failures():
    prop = {
        "property_name": "A",
        "property_address": "test",
        "income_line_items": {"gross_rents": 1000, "other_income": 100},
        "expense_line_items": {
            "advertising": 100,
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
            "other_deductions": 0,
        },
        "totals": {
            "total_rental_income": 9999,
            "total_expenses": 9999,
            "net_income": 9999,
        },
    }
    errors = validate_property(prop)
    assert len(errors) == 3
    assert any("line2c" in e for e in errors)
    assert any("line18" in e for e in errors)
    assert any("line19" in e for e in errors)


def test_missing_pdf_is_controlled_failure(tmp_path):
    with pytest.raises(ExtractionError, match="PDF not found"):
        extract_8825(tmp_path / "missing.pdf")


def test_corrupt_pdf_is_controlled_failure(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.7\nnot a real pdf")
    with pytest.raises(ExtractionError, match="Unreadable/corrupt PDF"):
        extract_8825(bad)


def test_image_or_blank_pdf_is_detected_as_no_usable_text_layer(tmp_path):
    blank = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(blank))
    c.rect(100, 100, 50, 50)
    c.save()

    ok, diag = usable_text_layer(blank)
    assert not ok, diag
    with pytest.raises(ExtractionError, match="Likely scanned/image-only input"):
        extract_8825(blank)

def test_multi_property_fixture_is_reproducible():
    import hashlib
    import subprocess

    pdf = ROOT / "data" / "f8825_multi_ABC.pdf"
    script = ROOT / "scripts" / "generate_multi_property_pdf.py"

    subprocess.run(
        [sys.executable, str(script)],
        check=True,
    )
    first = hashlib.sha256(pdf.read_bytes()).hexdigest()

    subprocess.run(
        [sys.executable, str(script)],
        check=True,
    )
    second = hashlib.sha256(pdf.read_bytes()).hexdigest()

    assert first == second


def test_versioned_profiles_detect_real_and_synthetic_layouts():
    from pypdf import PdfReader
    from form8825.profiles import detect_profile

    real = detect_profile(PdfReader(str(ROOT / "data/f8825.pdf")).get_fields() or {})
    synthetic = detect_profile(PdfReader(str(ROOT / "data/f8825_multi_ABC.pdf")).get_fields() or {})

    assert real is not None and real.profile_id == "irs-8825-2025-12"
    assert synthetic is not None and synthetic.profile_id == "synthetic-8825-2025-12"


def test_unknown_acroform_layout_fails_closed(tmp_path):
    unknown = tmp_path / "unknown-layout.pdf"
    c = canvas.Canvas(str(unknown))
    c.acroForm.textfield(name="unknown.field", value="123", x=50, y=700, width=100, height=20)
    c.showPage()
    c.save()

    with pytest.raises(ExtractionError, match="Unsupported Form 8825 AcroForm layout"):
        extract_8825(unknown)


def test_flattened_multi_property_fixture_matches_expected_json():
    actual = extract_8825(ROOT / "data/f8825_multi_ABC_flattened.pdf")
    expected = json.loads((ROOT / "data/f8825_multi_ABC_expected.json").read_text())
    assert actual == expected
