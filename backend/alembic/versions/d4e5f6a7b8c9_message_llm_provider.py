"""Record which LLM provider answered each bot turn (sarvam | gemini | anthropic | mock).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as b:
        b.add_column(sa.Column("llm_provider", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("messages") as b:
        b.drop_column("llm_provider")
