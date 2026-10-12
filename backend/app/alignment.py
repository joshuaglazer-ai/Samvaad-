"""Family Alignment Cards: compare the learner's and parent's priority rankings, gently."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .config import ALIGNMENT_VALUES

TOP_N = 2           # "both value X" = X is in both top-2s
MIN_GAP = 2         # a difference of ≥2 places is worth talking about


def validate_ranking(ranking: list[str]) -> None:
    if sorted(ranking) != sorted(ALIGNMENT_VALUES) or len(ranking) != len(ALIGNMENT_VALUES):
        raise ValueError(f"ranking must contain each of {ALIGNMENT_VALUES} exactly once")


def compare(learner: list[str] | None, parent: list[str] | None) -> dict:
    if not learner or not parent:
        return {"complete": False, "learner": learner, "parent": parent, "shared_top": [],
                "biggest_difference": None, "differences": []}
    lr = {v: i + 1 for i, v in enumerate(learner)}
    pr = {v: i + 1 for i, v in enumerate(parent)}
    shared = [v for v in learner[:TOP_N] if v in parent[:TOP_N]]
    diffs = sorted(
        ({"value": v, "learner_rank": lr[v], "parent_rank": pr[v], "gap": abs(lr[v] - pr[v])} for v in ALIGNMENT_VALUES),
        key=lambda d: (-d["gap"], min(d["learner_rank"], d["parent_rank"])),
    )
    biggest = diffs[0]["value"] if diffs and diffs[0]["gap"] >= MIN_GAP else None
    return {"complete": True, "learner": learner, "parent": parent, "shared_top": shared,
            "biggest_difference": biggest, "differences": diffs}


def latest_rankings(db: Session, session_id: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    rows = db.scalars(select(m.AlignmentResponse).where(m.AlignmentResponse.session_id == session_id)
                      .order_by(m.AlignmentResponse.created_at, m.AlignmentResponse.id))
    for r in rows:
        out[r.respondent] = r.ranking
    return out


def session_alignment(db: Session, session_id: str) -> dict:
    r = latest_rankings(db, session_id)
    return compare(r.get("learner"), r.get("parent"))
