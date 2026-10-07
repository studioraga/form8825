from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./form8825.db")
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)

if DB_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    extraction_status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reprocessed_from_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    processing_generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    properties = relationship("Property", back_populates="document", cascade="all, delete-orphan")


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("document_id", "property_name", name="uq_property_document_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    property_name: Mapped[str] = mapped_column(String(8))
    property_address: Mapped[str] = mapped_column(String(512), default="")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    document = relationship("Document", back_populates="properties")
    values = relationship("LineValue", back_populates="property", cascade="all, delete-orphan")
    audits = relationship("ChangeAudit", back_populates="property", cascade="all, delete-orphan")


class LineValue(Base):
    __tablename__ = "line_values"
    __table_args__ = (
        UniqueConstraint("property_id", "category", "key", name="uq_line_value_property_category_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16), default="extracted")

    property = relationship("Property", back_populates="values")


class ChangeAudit(Base):
    __tablename__ = "change_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    key: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[int] = mapped_column(Integer)
    new_value: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="manual UI edit")
    actor_id: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    client_ip: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    property = relationship("Property", back_populates="audits")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
