from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", "sqlite:///./artifacts/openapi_contract.db")
sys.path.insert(0, str(ROOT))

from api.main import app  # noqa: E402


def test_openapi_snapshot_matches_runtime_contract():
    committed = json.loads((ROOT / "docs/openapi.json").read_text())
    assert committed == app.openapi()


def test_required_routes_and_security_contracts_are_present():
    spec = app.openapi()
    paths = spec["paths"]
    for route in (
        "/health",
        "/documents",
        "/documents/{document_id}",
        "/properties/{property_id}/value",
        "/properties/{property_id}/audit",
        "/jobs",
        "/jobs/{job_id}",
    ):
        assert route in paths

    patch = paths["/properties/{property_id}/value"]["patch"]
    assert patch.get("security"), patch
    upload = paths["/documents"]["post"]
    assert upload.get("security"), upload

    schemas = spec["components"]["schemas"]
    update = schemas["UpdateValue"]
    assert {"category", "key", "value", "expected_version"} <= set(update["required"])
    assert update["properties"]["expected_version"]["minimum"] == 1

    schemes = spec["components"]["securitySchemes"]
    assert any(v.get("type") == "apiKey" and v.get("name") == "X-API-Key" for v in schemes.values())
