"""initial Form 8825 schema

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("extraction_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_name", sa.String(8), nullable=False),
        sa.Column("property_address", sa.String(512), nullable=False),
        sa.UniqueConstraint("document_id", "property_name", name="uq_property_document_name"),
    )
    op.create_index("ix_properties_document_id", "properties", ["document_id"])
    op.create_table(
        "line_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.UniqueConstraint("property_id", "category", "key", name="uq_line_value_property_category_key"),
    )
    op.create_index("ix_line_values_property_id", "line_values", ["property_id"])
    op.create_table(
        "change_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Integer(), nullable=False),
        sa.Column("new_value", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_change_audit_property_id", "change_audit", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_change_audit_property_id", table_name="change_audit")
    op.drop_table("change_audit")
    op.drop_index("ix_line_values_property_id", table_name="line_values")
    op.drop_table("line_values")
    op.drop_index("ix_properties_document_id", table_name="properties")
    op.drop_table("properties")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_table("documents")
