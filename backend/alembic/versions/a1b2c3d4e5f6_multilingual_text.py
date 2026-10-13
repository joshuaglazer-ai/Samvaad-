"""Translatable text as JSON {lang: text}; escalation summary in English + session language.

Revision ID: a1b2c3d4e5f6
Revises: 8f9c299c5b17
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "8f9c299c5b17"
branch_labels = None
depends_on = None


def _load(v):
    if v is None:
        return []
    return v if isinstance(v, list) else json.loads(v)


def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("trades") as b:
        b.add_column(sa.Column("names", sa.JSON(), nullable=True))
        b.add_column(sa.Column("entry_requirement", sa.JSON(), nullable=True))
        b.add_column(sa.Column("job_roles", sa.JSON(), nullable=True))
    with op.batch_alter_table("progression_steps") as b:
        b.add_column(sa.Column("titles", sa.JSON(), nullable=True))
        b.add_column(sa.Column("entry_requirement", sa.JSON(), nullable=True))
    with op.batch_alter_table("costs_support") as b:
        b.add_column(sa.Column("description", sa.JSON(), nullable=True))
    with op.batch_alter_table("escalations") as b:
        b.add_column(sa.Column("summary_local", sa.Text(), nullable=True))
        b.add_column(sa.Column("summary_language", sa.String(5), nullable=True))

    # Copy existing en/kn text into the JSON fields (hi/te fall back to English until added).
    t = sa.table("trades", sa.column("id"), sa.column("name_en"), sa.column("name_kn"), sa.column("entry_requirement_en"),
                 sa.column("entry_requirement_kn"), sa.column("job_roles_en"), sa.column("job_roles_kn"),
                 sa.column("names", sa.JSON), sa.column("entry_requirement", sa.JSON), sa.column("job_roles", sa.JSON))
    for r in bind.execute(sa.select(t)).mappings():
        bind.execute(t.update().where(t.c.id == r["id"]).values(
            names={"en": r["name_en"], "kn": r["name_kn"]},
            entry_requirement={"en": r["entry_requirement_en"], "kn": r["entry_requirement_kn"]},
            job_roles={"en": _load(r["job_roles_en"]), "kn": _load(r["job_roles_kn"])}))
    p = sa.table("progression_steps", sa.column("id"), sa.column("title_en"), sa.column("title_kn"),
                 sa.column("entry_requirement_en"), sa.column("entry_requirement_kn"),
                 sa.column("titles", sa.JSON), sa.column("entry_requirement", sa.JSON))
    for r in bind.execute(sa.select(p)).mappings():
        bind.execute(p.update().where(p.c.id == r["id"]).values(
            titles={"en": r["title_en"], "kn": r["title_kn"]},
            entry_requirement={"en": r["entry_requirement_en"], "kn": r["entry_requirement_kn"]}))
    c = sa.table("costs_support", sa.column("id"), sa.column("description_en"), sa.column("description_kn"),
                 sa.column("description", sa.JSON))
    for r in bind.execute(sa.select(c)).mappings():
        bind.execute(c.update().where(c.c.id == r["id"]).values(
            description={"en": r["description_en"], "kn": r["description_kn"]}))
    e = sa.table("escalations", sa.column("id"), sa.column("summary_kn"), sa.column("summary_local"),
                 sa.column("summary_language"))
    bind.execute(e.update().values(summary_local=e.c.summary_kn, summary_language="kn"))

    with op.batch_alter_table("trades") as b:
        for col in ("name_en", "name_kn", "entry_requirement_en", "entry_requirement_kn", "job_roles_en", "job_roles_kn"):
            b.drop_column(col)
    with op.batch_alter_table("progression_steps") as b:
        for col in ("title_en", "title_kn", "entry_requirement_en", "entry_requirement_kn"):
            b.drop_column(col)
    with op.batch_alter_table("costs_support") as b:
        b.drop_column("description_en")
        b.drop_column("description_kn")
    with op.batch_alter_table("escalations") as b:
        b.drop_column("summary_kn")


def downgrade() -> None:
    raise NotImplementedError("one-way data migration (multilingual JSON text)")
