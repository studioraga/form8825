"""add structured audit identity

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("change_audit") as batch:
        batch.add_column(sa.Column("actor_id", sa.String(128), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("actor_role", sa.String(32), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("request_id", sa.String(128), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("client_ip", sa.String(64), nullable=False, server_default="unknown"))


def downgrade() -> None:
    with op.batch_alter_table("change_audit") as batch:
        batch.drop_column("client_ip")
        batch.drop_column("request_id")
        batch.drop_column("actor_role")
        batch.drop_column("actor_id")
