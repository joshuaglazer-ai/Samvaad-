"""Update 3: sectors and trade_synonyms tables, trade traits/data_status, learner aspiration and parent hope.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
"""
import re

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _aspiration_columns(prefix: str) -> list[sa.Column]:
    match = "matched_trade_slugs" if prefix == "aspiration_" else f"{prefix}matched_trade_slugs"
    conf = "match_confidence" if prefix == "aspiration_" else f"{prefix}match_confidence"
    return [
        sa.Column(f"{prefix}text", sa.Text(), nullable=True),
        sa.Column(f"{prefix}language", sa.String(5), nullable=True),
        sa.Column(f"{prefix}source", sa.String(10), nullable=True),
        sa.Column(match, sa.JSON(), nullable=True),
        sa.Column(conf, sa.Float(), nullable=True),
        sa.Column(f"{prefix}category", sa.String(20), nullable=True),
        sa.Column(f"{prefix}confirmed", sa.Boolean(), nullable=False, server_default="0"),
    ]


def upgrade() -> None:
    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("names", sa.JSON(), nullable=False),
        sa.Column("icon", sa.String(40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_sectors_slug", "sectors", ["slug"], unique=True)
    op.create_table(
        "trade_synonyms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("term", sa.String(120), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
    )
    op.create_index("ix_trade_synonyms_trade_id", "trade_synonyms", ["trade_id"])
    op.create_index("ix_trade_synonyms_language", "trade_synonyms", ["language"])

    with op.batch_alter_table("trades") as b:
        b.add_column(sa.Column("traits", sa.JSON(), nullable=True))
        b.add_column(sa.Column("data_status", sa.String(20), nullable=False, server_default="demo"))
    with op.batch_alter_table("sessions") as b:
        for col in _aspiration_columns("aspiration_") + _aspiration_columns("parent_hope_"):
            b.add_column(col)

    # Trades stored the sector's English name; they now point at sectors.slug. Existing sectors get a row with
    # their English name (the seed adds the other languages).
    bind = op.get_bind()
    t = sa.table("trades", sa.column("id"), sa.column("sector"))
    s = sa.table("sectors", sa.column("slug"), sa.column("names", sa.JSON), sa.column("icon"), sa.column("sort_order"))
    seen: dict[str, str] = {}
    for r in bind.execute(sa.select(t)).mappings():
        slug = _slug(r["sector"] or "other")
        if slug not in seen:
            seen[slug] = r["sector"] or "Other"
        bind.execute(t.update().where(t.c.id == r["id"]).values(sector=slug))
    for i, (slug, name) in enumerate(sorted(seen.items())):
        bind.execute(s.insert().values(slug=slug, names={"en": name}, icon="tool", sort_order=i))


def downgrade() -> None:
    bind = op.get_bind()
    s = sa.table("sectors", sa.column("slug"), sa.column("names", sa.JSON))
    t = sa.table("trades", sa.column("id"), sa.column("sector"))
    names = {r["slug"]: (r["names"] or {}).get("en", r["slug"]) for r in bind.execute(sa.select(s)).mappings()}
    for r in bind.execute(sa.select(t)).mappings():
        bind.execute(t.update().where(t.c.id == r["id"]).values(sector=names.get(r["sector"], r["sector"])))
    with op.batch_alter_table("sessions") as b:
        for col in reversed(_aspiration_columns("aspiration_") + _aspiration_columns("parent_hope_")):
            b.drop_column(col.name)
    with op.batch_alter_table("trades") as b:
        b.drop_column("data_status")
        b.drop_column("traits")
    op.drop_index("ix_trade_synonyms_language", "trade_synonyms")
    op.drop_index("ix_trade_synonyms_trade_id", "trade_synonyms")
    op.drop_table("trade_synonyms")
    op.drop_index("ix_sectors_slug", "sectors")
    op.drop_table("sectors")
