from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from form8825.extractor import ExtractionError, extract_8825  # noqa: E402
from .db import Base, ChangeAudit, Document, LineValue, Property, SessionLocal, engine  # noqa: E402
from .auth import Principal, require_role  # noqa: E402

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))

app = FastAPI(title="Form 8825 Extraction API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def serialize_property(p: Property) -> dict:
    out = {
        "id": p.id,
        "property_name": p.property_name,
        "property_address": p.property_address,
        "version": p.version,
        "income_line_items": {},
        "expense_line_items": {},
        "totals": {},
    }
    for value in p.values:
        out[value.category][value.key] = value.value
    return out


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...), s: Session = Depends(db), _principal: Principal = Depends(require_role("reviewer"))):
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"PDF exceeds {MAX_UPLOAD_BYTES} byte upload limit")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(400, "File is not a PDF")

    sha256 = hashlib.sha256(raw).hexdigest()
    policy = os.getenv("DUPLICATE_DOCUMENT_POLICY", "reuse").lower()
    if policy not in {"reuse", "reject", "reprocess"}:
        raise HTTPException(500, f"Invalid DUPLICATE_DOCUMENT_POLICY: {policy}")
    existing = s.query(Document).filter_by(sha256=sha256).order_by(Document.id.desc()).first()
    if existing and policy == "reuse":
        return {
            "document_id": existing.id,
            "duplicate_action": "reused",
            "properties": [serialize_property(p) for p in existing.properties],
        }
    if existing and policy == "reject":
        raise HTTPException(409, f"Duplicate document SHA-256 already stored as document {existing.id}")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name

    try:
        result = extract_8825(path)
    except ExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    try:
        doc = Document(
            filename=file.filename or "upload.pdf",
            sha256=sha256,
            extraction_status="completed",
            reprocessed_from_id=existing.id if existing and policy == "reprocess" else None,
            processing_generation=(existing.processing_generation + 1) if existing and policy == "reprocess" else 1,
        )
        s.add(doc)
        s.flush()

        for item in result:
            prop = Property(
                document_id=doc.id,
                property_name=item["property_name"],
                property_address=item["property_address"],
            )
            s.add(prop)
            s.flush()
            for category in ("income_line_items", "expense_line_items", "totals"):
                for key, value in item[category].items():
                    s.add(
                        LineValue(
                            property_id=prop.id,
                            category=category,
                            key=key,
                            value=value,
                            source="extracted",
                        )
                    )

        s.commit()
        s.refresh(doc)
    except SQLAlchemyError as exc:
        s.rollback()
        raise HTTPException(500, "Database persistence failed") from exc

    return {"document_id": doc.id, "duplicate_action": "reprocessed" if doc.reprocessed_from_id else "created", "properties": [serialize_property(p) for p in doc.properties]}


@app.get("/documents/{document_id}")
def get_document(document_id: int, s: Session = Depends(db), _principal: Principal = Depends(require_role("viewer"))):
    doc = s.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "sha256": doc.sha256,
        "extraction_status": doc.extraction_status,
        "reprocessed_from_id": doc.reprocessed_from_id,
        "processing_generation": doc.processing_generation,
        "properties": [serialize_property(p) for p in doc.properties],
    }


class UpdateValue(BaseModel):
    category: str
    key: str
    value: int
    expected_version: int = Field(ge=1)
    reason: str = Field(default="manual UI edit", min_length=1, max_length=500)


@app.patch("/properties/{property_id}/value")
def update_value(property_id: int, body: UpdateValue, request: Request, s: Session = Depends(db), principal: Principal = Depends(require_role("reviewer"))):
    prop = s.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")

    if body.expected_version != prop.version:
        raise HTTPException(409, f"Stale property version: expected {body.expected_version}, current {prop.version}")

    if body.category not in {"income_line_items", "expense_line_items"}:
        raise HTTPException(
            400,
            "Only source income/expense line items are manually editable; totals are recalculated",
        )

    value = (
        s.query(LineValue)
        .filter_by(property_id=property_id, category=body.category, key=body.key)
        .one_or_none()
    )
    if not value:
        raise HTTPException(404, "Line item not found")

    try:
        old = value.value
        value.value = body.value
        value.source = "manual"
        s.add(
            ChangeAudit(
                property_id=property_id,
                category=body.category,
                key=body.key,
                old_value=old,
                new_value=body.value,
                reason=body.reason,
                actor_id=principal.subject,
                actor_role=principal.role,
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4()),
                client_ip=request.client.host if request.client else "unknown",
            )
        )

        data = serialize_property(prop)
        total_income = sum(data["income_line_items"].values())
        total_expenses = sum(data["expense_line_items"].values())
        net_income = total_income - total_expenses

        for key, recalculated in (
            ("total_rental_income", total_income),
            ("total_expenses", total_expenses),
            ("net_income", net_income),
        ):
            total_value = (
                s.query(LineValue)
                .filter_by(property_id=property_id, category="totals", key=key)
                .one()
            )
            total_value.value = recalculated
            total_value.source = "calculated"

        prop.version += 1
        s.commit()
        s.refresh(prop)
    except SQLAlchemyError as exc:
        s.rollback()
        raise HTTPException(500, "Database update failed") from exc

    return serialize_property(prop)


@app.get("/properties/{property_id}/audit")
def audit(property_id: int, s: Session = Depends(db), _principal: Principal = Depends(require_role("viewer"))):
    if not s.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    rows = (
        s.query(ChangeAudit)
        .filter_by(property_id=property_id)
        .order_by(ChangeAudit.id)
        .all()
    )
    return [
        {
            "id": row.id,
            "category": row.category,
            "key": row.key,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "reason": row.reason,
            "actor_id": row.actor_id,
            "actor_role": row.actor_role,
            "request_id": row.request_id,
            "client_ip": row.client_ip,
            "changed_at": row.changed_at,
        }
        for row in rows
    ]
