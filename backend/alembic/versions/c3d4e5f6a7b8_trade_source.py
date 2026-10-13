"""Update 3 · Step 5: trades can carry the source that backs them (needed before they can be verified/historical).

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trades") as b:
        b.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        b.create_foreign_key("fk_trades_source_id", "sources", ["source_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("trades") as b:
        b.drop_constraint("fk_trades_source_id", type_="foreignkey")
        b.drop_column("source_id")
