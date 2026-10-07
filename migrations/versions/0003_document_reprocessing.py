"""add duplicate/reprocessing metadata

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("reprocessed_from_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("processing_generation", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key("fk_documents_reprocessed_from", "documents", ["reprocessed_from_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.drop_constraint("fk_documents_reprocessed_from", type_="foreignkey")
        batch.drop_column("processing_generation")
        batch.drop_column("reprocessed_from_id")
