from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
TEST_DB = ROOT / "artifacts/test_api.db"
os.environ["DATABASE_URL"] = "sqlite:///" + str(TEST_DB)
os.environ["MAX_UPLOAD_BYTES"] = str(2 * 1024 * 1024)
sys.path.insert(0, str(ROOT))

if TEST_DB.exists():
    TEST_DB.unlink()

import api.db as dbm  # noqa: E402
import api.main as main  # noqa: E402

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_database():
    dbm.Base.metadata.drop_all(dbm.engine)
    dbm.Base.metadata.create_all(dbm.engine)
    yield


def upload_multi():
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("multi.pdf", f, "application/pdf")},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_multi_property_and_get_document():
    body = upload_multi()
    assert len(body["properties"]) == 3
    assert [p["property_name"] for p in body["properties"]] == ["A", "B", "C"]

    response = client.get(f"/documents/{body['document_id']}")
    assert response.status_code == 200
    persisted = response.json()
    assert persisted["filename"] == "multi.pdf"
    assert len(persisted["sha256"]) == 64
    assert persisted["extraction_status"] == "completed"
    assert persisted["properties"] == body["properties"]


def test_income_edit_recalculates_and_is_audited():
    body = upload_multi()
    prop = body["properties"][0]
    old = prop["income_line_items"]["gross_rents"]
    old_net = prop["totals"]["net_income"]

    response = client.patch(
        f"/properties/{prop['id']}/value",
        json={
            "category": "income_line_items",
            "key": "gross_rents",
            "value": old + 1000,
            "reason": "test adjustment",
        },
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["totals"]["total_rental_income"] == 126_000
    assert updated["totals"]["total_expenses"] == 89_000
    assert updated["totals"]["net_income"] == old_net + 1000 == 37_000

    audit = client.get(f"/properties/{prop['id']}/audit")
    assert audit.status_code == 200
    last = audit.json()[-1]
    assert last["old_value"] == old
    assert last["new_value"] == old + 1000
    assert last["reason"] == "test adjustment"


def test_expense_edit_recalculates_total_and_net():
    body = upload_multi()
    prop = body["properties"][0]
    old_repairs = prop["expense_line_items"]["repairs"]

    response = client.patch(
        f"/properties/{prop['id']}/value",
        json={
            "category": "expense_line_items",
            "key": "repairs",
            "value": old_repairs + 500,
            "reason": "repair correction",
        },
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["totals"]["total_rental_income"] == 125_000
    assert updated["totals"]["total_expenses"] == 89_500
    assert updated["totals"]["net_income"] == 35_500


def test_totals_cannot_be_manually_modified():
    prop = upload_multi()["properties"][0]
    response = client.patch(
        f"/properties/{prop['id']}/value",
        json={"category": "totals", "key": "net_income", "value": 999999},
    )
    assert response.status_code == 400


def test_unknown_document_property_and_line_are_404():
    assert client.get("/documents/999999").status_code == 404
    assert client.get("/properties/999999/audit").status_code == 404
    response = client.patch(
        "/properties/999999/value",
        json={"category": "income_line_items", "key": "gross_rents", "value": 1},
    )
    assert response.status_code == 404

    prop = upload_multi()["properties"][0]
    response = client.patch(
        f"/properties/{prop['id']}/value",
        json={"category": "income_line_items", "key": "not_a_line", "value": 1},
    )
    assert response.status_code == 404


def test_non_pdf_and_corrupt_pdf_are_rejected():
    response = client.post(
        "/documents",
        files={"file": ("bad.pdf", b"not really a pdf", "application/pdf")},
    )
    assert response.status_code == 400

    response = client.post(
        "/documents",
        files={"file": ("corrupt.pdf", b"%PDF-1.7\nnot-real", "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_size_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 16)
    response = client.post(
        "/documents",
        files={"file": ("too-large.pdf", b"%PDF-" + b"x" * 32, "application/pdf")},
    )
    assert response.status_code == 413
