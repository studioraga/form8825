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
            "expected_version": prop["version"],
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
            "expected_version": prop["version"],
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
        json={"category": "totals", "key": "net_income", "value": 999999, "expected_version": prop["version"]},
    )
    assert response.status_code == 400


def test_unknown_document_property_and_line_are_404():
    assert client.get("/documents/999999").status_code == 404
    assert client.get("/properties/999999/audit").status_code == 404
    response = client.patch(
        "/properties/999999/value",
        json={"category": "income_line_items", "key": "gross_rents", "value": 1, "expected_version": 1},
    )
    assert response.status_code == 404

    prop = upload_multi()["properties"][0]
    response = client.patch(
        f"/properties/{prop['id']}/value",
        json={"category": "income_line_items", "key": "not_a_line", "value": 1, "expected_version": prop["version"]},
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


def test_rbac_api_key_roles(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "enabled")
    monkeypatch.setenv(
        "FORM8825_API_KEYS",
        "view-key:viewer:alice,review-key:reviewer:bob,admin-key:admin:root",
    )
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        unauth = client.post("/documents", files={"file": ("multi.pdf", f, "application/pdf")})
    assert unauth.status_code == 401

    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        forbidden = client.post(
            "/documents",
            headers={"X-API-Key": "view-key"},
            files={"file": ("multi.pdf", f, "application/pdf")},
        )
    assert forbidden.status_code == 403

    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        allowed = client.post(
            "/documents",
            headers={"X-API-Key": "review-key"},
            files={"file": ("multi.pdf", f, "application/pdf")},
        )
    assert allowed.status_code == 200
    doc_id = allowed.json()["document_id"]
    assert client.get(f"/documents/{doc_id}", headers={"X-API-Key": "view-key"}).status_code == 200


def test_optimistic_concurrency_rejects_stale_edit():
    prop = upload_multi()["properties"][0]
    first = client.patch(
        f"/properties/{prop['id']}/value",
        json={
            "category": "income_line_items",
            "key": "gross_rents",
            "value": 121000,
            "expected_version": prop["version"],
        },
    )
    assert first.status_code == 200
    assert first.json()["version"] == prop["version"] + 1

    stale = client.patch(
        f"/properties/{prop['id']}/value",
        json={
            "category": "income_line_items",
            "key": "other_income",
            "value": 6000,
            "expected_version": prop["version"],
        },
    )
    assert stale.status_code == 409


def test_duplicate_document_policies(monkeypatch):
    monkeypatch.setenv("DUPLICATE_DOCUMENT_POLICY", "reuse")
    first = upload_multi()
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        reused = client.post("/documents", files={"file": ("again.pdf", f, "application/pdf")})
    assert reused.status_code == 200
    assert reused.json()["document_id"] == first["document_id"]
    assert reused.json()["duplicate_action"] == "reused"

    monkeypatch.setenv("DUPLICATE_DOCUMENT_POLICY", "reject")
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        rejected = client.post("/documents", files={"file": ("again.pdf", f, "application/pdf")})
    assert rejected.status_code == 409

    monkeypatch.setenv("DUPLICATE_DOCUMENT_POLICY", "reprocess")
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        reprocessed = client.post("/documents", files={"file": ("again.pdf", f, "application/pdf")})
    assert reprocessed.status_code == 200
    body = reprocessed.json()
    assert body["document_id"] != first["document_id"]
    assert body["duplicate_action"] == "reprocessed"
    stored = client.get(f"/documents/{body['document_id']}").json()
    assert stored["reprocessed_from_id"] == first["document_id"]
    assert stored["processing_generation"] == 2


def test_audit_captures_actor_request_and_client_identity(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "enabled")
    monkeypatch.setenv("FORM8825_API_KEYS", "review-key:reviewer:reviewer-42")
    with open(ROOT / "data/f8825_multi_ABC.pdf", "rb") as f:
        upload = client.post(
            "/documents",
            headers={"X-API-Key": "review-key"},
            files={"file": ("multi.pdf", f, "application/pdf")},
        )
    prop = upload.json()["properties"][0]
    edit = client.patch(
        f"/properties/{prop['id']}/value",
        headers={"X-API-Key": "review-key", "X-Request-ID": "req-audit-001"},
        json={
            "category": "income_line_items",
            "key": "gross_rents",
            "value": 121000,
            "expected_version": prop["version"],
            "reason": "identity test",
        },
    )
    assert edit.status_code == 200
    rows = client.get(
        f"/properties/{prop['id']}/audit",
        headers={"X-API-Key": "review-key"},
    ).json()
    row = rows[-1]
    assert row["actor_id"] == "reviewer-42"
    assert row["actor_role"] == "reviewer"
    assert row["request_id"] == "req-audit-001"
    assert row["client_ip"]
