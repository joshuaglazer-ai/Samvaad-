"""Create 200 SIMULATED family sessions for the admin dashboard.

Each simulated family is run through the real chat pipeline in mock mode, so cards, evidence gaps,
sentiment tags and escalation triggers come from the actual code paths; only the timestamps are
back-dated afterwards. Every simulated session has sessions.simulated = true and every event payload
carries "simulated": true. The dashboard shows a "simulated" banner. These are NOT real families.

    python -m seed.simulate_sessions [--n 200] [--seed 7]
"""
from __future__ import annotations

import argparse
import random
from datetime import timedelta

from sqlalchemy import delete, select

from app import models as m
from app.alignment import compare
from app.chat import handle_turn
from app.config import ALIGNMENT_VALUES
from app.db import SessionLocal
from app.escalation import now
from app.llm import MockLLM
from app.schema_setup import upgrade_to_head

# District patterns (demo assumptions, not findings): which worries come up, how resistant parents
# sound, and how many families use Kannada.
DISTRICTS = {
    "Bengaluru Urban": {"weight": 0.30, "kn": 0.45, "neg": 0.22,
                        "concerns": {"income": 3, "social_status": 3, "degree_first": 3, "job_security": 2, "cost": 1}},
    "Mysuru": {"weight": 0.25, "kn": 0.70, "neg": 0.32,
               "concerns": {"job_security": 3, "cost": 3, "degree_first": 2, "income": 2, "distance_migration": 1}},
    "Kalaburagi": {"weight": 0.22, "kn": 0.85, "neg": 0.55,
                   "concerns": {"safety": 4, "distance_migration": 3, "cost": 3, "income": 2, "social_status": 1}},
    "Dharwad": {"weight": 0.23, "kn": 0.75, "neg": 0.42,
                "concerns": {"degree_first": 4, "social_status": 3, "safety": 2, "job_security": 1, "cost": 1}},
}
INCOME = {"Bengaluru Urban": [1, 3, 4, 3, 2], "Mysuru": [3, 4, 3, 1, 2], "Kalaburagi": [6, 3, 1, 0, 2], "Dharwad": [4, 4, 2, 1, 2]}
BRACKETS = ["<1.5L", "1.5-3L", "3-6L", ">6L", "prefer_not_to_say"]
EDU = (["class_8", "class_10", "class_12", "iti", "diploma"], [1, 6, 3, 2, 1])
INTERESTS = ["machines", "helping", "electricity", "vehicles", "nature_solar", "computers"]

TRADES = {  # (English mention, Kannada mention) — both recognised by the counsellor
    "electrician": ("electrician", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್"),
    "wireman": ("wireman", "ವೈರ್‌ಮ್ಯಾನ್"),
    "solar": ("solar panel installer", "ಸೌರ ಫಲಕ ತಂತ್ರಜ್ಞ"),
    "two": ("two-wheeler mechanic", "ದ್ವಿಚಕ್ರ ಮೆಕ್ಯಾನಿಕ್"),
    "car": ("car mechanic", "ಕಾರು ಮೆಕ್ಯಾನಿಕ್"),
    "ev": ("EV technician", "ಇವಿ ತಂತ್ರಜ್ಞ"),
    "gda": ("hospital assistant", "ಆಸ್ಪತ್ರೆ ಸಹಾಯಕ"),
    "hha": ("home health aide", "ಮನೆ ಆರೈಕೆ ಸಹಾಯಕ"),
}
QUESTIONS = {
    "income": (["How much will a {t} earn?", "Is a {t}'s salary enough to run a family?"],
               ["{t} ಆಗಿ ಎಷ್ಟು ಸಂಪಾದಿಸಬಹುದು?", "{t} ಸಂಬಳ ಕುಟುಂಬ ನಡೆಸಲು ಸಾಕಾಗುತ್ತದೆಯೇ?"]),
    "job_security": (["Will there be a steady job as a {t}?", "Do {t} learners get placed after training?"],
                     ["{t} ಆಗಿ ಸ್ಥಿರ ಉದ್ಯೋಗ ಸಿಗುತ್ತದೆಯೇ?", "{t} ತರಬೇತಿಯ ನಂತರ ಕೆಲಸ ಸಿಗುತ್ತದೆಯೇ?"]),
    "social_status": (["Will relatives respect {t} work?", "Is there respect in society for a {t}?"],
                      ["{t} ಕೆಲಸಕ್ಕೆ ಸಮಾಜದಲ್ಲಿ ಗೌರವ ಇದೆಯೇ?", "ಸಂಬಂಧಿಕರು {t} ಕೆಲಸವನ್ನು ಗೌರವಿಸುತ್ತಾರೆಯೇ?"]),
    "safety": (["Is {t} work safe?", "Are there accidents in {t} work?"],
               ["{t} ಕೆಲಸ ಸುರಕ್ಷಿತವೇ?", "{t} ಕೆಲಸದಲ್ಲಿ ಅಪಾಯ ಇದೆಯೇ?"]),
    "cost": (["How much does {t} training cost?", "Is there any scholarship for {t} training?"],
             ["{t} ತರಬೇತಿಗೆ ಎಷ್ಟು ಖರ್ಚಾಗುತ್ತದೆ?", "{t} ತರಬೇತಿಗೆ ವಿದ್ಯಾರ್ಥಿವೇತನ ಇದೆಯೇ?"]),
    "distance_migration": (["Is there a {t} training centre near us?", "Where can we learn {t} work nearby?"],
                           ["ಹತ್ತಿರದಲ್ಲಿ {t} ತರಬೇತಿ ಕೇಂದ್ರ ಇದೆಯೇ?", "{t} ಕೆಲಸ ಹತ್ತಿರದಲ್ಲಿ ಎಲ್ಲಿ ಕಲಿಯಬಹುದು?"]),
    "degree_first": (["Should we choose a degree first instead of {t}?", "Can a {t} study further later?"],
                     ["{t} ಬದಲು ಮೊದಲು ಪದವಿ ಮಾಡಿಸಬೇಕೇ?", "{t} ಆದ ಮೇಲೆ ಮುಂದೆ ಓದಬಹುದೇ?"]),
}
GAP_QUESTIONS = (["How much does a plumber earn?", "What does a tailor earn?", "Is drone technician a good job?",
                  "How much does a beautician earn?"],
                 ["ಪ್ಲಂಬರ್ ಎಷ್ಟು ಸಂಪಾದಿಸುತ್ತಾರೆ?", "ಟೈಲರ್ ಎಷ್ಟು ಸಂಪಾದಿಸುತ್ತಾರೆ?", "ಡ್ರೋನ್ ತಂತ್ರಜ್ಞ ಒಳ್ಳೆಯ ಕೆಲಸವೇ?",
                  "ಬ್ಯೂಟಿ ಕೆಲಸದಲ್ಲಿ ಎಷ್ಟು ಸಂಪಾದನೆ?"])
SENSITIVE = (["Is it safe for my daughter to travel alone at night for this work?", "We have a big debt and I am stressed."],
             ["ನನ್ನ ಮಗಳು ರಾತ್ರಿ ಒಬ್ಬಳೇ ಕೆಲಸಕ್ಕೆ ಹೋಗುವುದು ಸುರಕ್ಷಿತವೇ?", "ನಮಗೆ ಸಾಲದ ಹೊರೆ ಇದೆ, ತುಂಬಾ ಚಿಂತೆ."])
NEG = (["I am worried.", "Honestly, it feels risky.", "I don't want my child to waste time.", "I am not sure, I have doubts."],
       ["ನನಗೆ ಚಿಂತೆ ಇದೆ.", "ಇದು ಕಷ್ಟ ಅನ್ನಿಸುತ್ತದೆ.", "ನನಗೆ ಅನುಮಾನ ಇದೆ.", "ಇದು ಬೇಡ ಅನ್ನಿಸುತ್ತದೆ, ಚಿಂತೆ ಇದೆ."])
POS = (["Thank you, this is helpful.", "Okay, that sounds good.", "This makes sense, thank you."],
       ["ಧನ್ಯವಾದ, ಇದು ಸಹಾಯವಾಯಿತು.", "ಸರಿ, ಒಳ್ಳೆಯದು.", "ಸಮಾಧಾನ ಆಯಿತು, ಧನ್ಯವಾದ."])

# Parents and learners tend to rank values differently (demo assumption, varies by district).
PARENT_BIAS = {"Kalaburagi": ["safety", "near_home"], "Dharwad": ["study_further", "respect"],
               "Mysuru": ["near_home", "earning_soon"], "Bengaluru Urban": ["study_further", "respect"]}
LEARNER_BIAS = ["earning_soon", "study_further"]


def weighted(rng: random.Random, options: dict[str, float] | list, weights=None):
    if isinstance(options, dict):
        return rng.choices(list(options), weights=list(options.values()))[0]
    return rng.choices(options, weights=weights)[0]


def ranking(rng: random.Random, bias: list[str]) -> list[str]:
    rest = [v for v in ALIGNMENT_VALUES if v not in bias]
    rng.shuffle(rest)
    top = bias[:]
    if rng.random() < 0.35:
        rng.shuffle(top)
    order = top + rest
    if rng.random() < 0.3:  # some families differ from the pattern
        i, j = rng.sample(range(5), 2)
        order[i], order[j] = order[j], order[i]
    return order


def clear_simulated(db) -> int:
    ids = list(db.scalars(select(m.SessionRow.id).where(m.SessionRow.simulated.is_(True))))
    if not ids:
        return 0
    case_ids = list(db.scalars(select(m.Escalation.id).where(m.Escalation.session_id.in_(ids))))
    if case_ids:
        db.execute(delete(m.CallbackRequest).where(m.CallbackRequest.escalation_id.in_(case_ids)))
    for model in (m.Escalation, m.GuardrailLog, m.EvidenceGap, m.Event, m.AlignmentResponse, m.Message):
        db.execute(delete(model).where(model.session_id.in_(ids)))
    db.execute(delete(m.SessionRow).where(m.SessionRow.id.in_(ids)))
    db.commit()
    return len(ids)


def simulate(db, n: int = 200, seed: int = 7, days: int = 120) -> dict:
    rng = random.Random(seed)
    llm = MockLLM()
    start = now() - timedelta(days=days)
    stats = {"sessions": 0, "turns": 0}
    names = list(DISTRICTS)
    for _ in range(n):
        district = rng.choices(names, weights=[DISTRICTS[d]["weight"] for d in names])[0]
        p = DISTRICTS[district]
        lang = "kn" if rng.random() < p["kn"] else "en"
        li = 1 if lang == "kn" else 0
        concerns = list(dict.fromkeys(weighted(rng, p["concerns"]) for _ in range(rng.randint(1, 3))))
        s = m.SessionRow(
            language=lang, district=district,
            income_bracket=weighted(rng, BRACKETS, INCOME[district]) if rng.random() < 0.85 else None,
            learner_education=weighted(rng, *EDU), learner_interests=rng.sample(INTERESTS, rng.randint(1, 2)),
            top_concerns=concerns, helper_mode=rng.random() < 0.15, consent_given=True, simulated=True,
        )
        db.add(s)
        db.flush()
        db.add(m.Event(session_id=s.id, event_type="session_started", payload={"language": lang, "district": district}))

        # alignment (most families complete it)
        if rng.random() < 0.78:
            db.add(m.AlignmentResponse(session_id=s.id, respondent="learner", ranking=ranking(rng, LEARNER_BIAS)))
            if rng.random() < 0.92:
                par = ranking(rng, PARENT_BIAS[district])
                db.add(m.AlignmentResponse(session_id=s.id, respondent="parent", ranking=par))
                db.flush()
                lr = db.scalar(select(m.AlignmentResponse.ranking).where(
                    m.AlignmentResponse.session_id == s.id, m.AlignmentResponse.respondent == "learner"))
                res = compare(lr, par)
                db.add(m.Event(session_id=s.id, event_type="alignment_completed",
                               payload={"shared_top": res["shared_top"], "biggest_difference": res["biggest_difference"]}))

        # self-reported mood before
        base = rng.choices([1, 2, 3, 4], weights=[3, 4, 3, 1] if p["neg"] > 0.4 else [1, 3, 4, 2])[0]
        s.mood_pre_parent = base
        s.mood_pre_learner = min(5, base + rng.choice([0, 1, 1, 2]))
        db.commit()

        trade = rng.choice(list(TRADES))
        if district == "Kalaburagi" and rng.random() < 0.3:
            trade = "ev"  # EV interest where data is thin → shows up as fallbacks/gaps
        turns = rng.randint(2, 6)
        for i in range(turns):
            speaker = "parent" if rng.random() < 0.6 else "learner"
            r = rng.random()
            if r < 0.06 and district in ("Kalaburagi", "Dharwad"):
                text = rng.choice(SENSITIVE[li])
            elif r < 0.13:
                text = rng.choice(GAP_QUESTIONS[li])
            else:
                c = rng.choice(concerns) if rng.random() < 0.7 else weighted(rng, p["concerns"])
                text = rng.choice(QUESTIONS[c][li]).format(t=TRADES[trade][li])
                # Parents' worry eases as the conversation goes on (sentiment shift).
                neg_p = p["neg"] * (1.0 - 0.18 * i) if speaker == "parent" else p["neg"] * 0.4
                if rng.random() < neg_p:
                    text = f"{rng.choice(NEG[li])} {text}"
                elif rng.random() < 0.12 + 0.08 * i:
                    text = f"{text} {rng.choice(POS[li])}"
            handle_turn(db, s.id, speaker, text, lang, llm=llm)
            stats["turns"] += 1
            if db.get(m.SessionRow, s.id).escalated and rng.random() < 0.5:
                break

        # most families finish with a post mood check
        s = db.get(m.SessionRow, s.id)
        if rng.random() < 0.68:
            lift = rng.choices([-1, 0, 1, 2], weights=[1, 3, 5, 2])[0]
            s.mood_post_parent = max(1, min(5, s.mood_pre_parent + lift))
            s.mood_post_learner = max(1, min(5, s.mood_pre_learner + rng.choices([-1, 0, 1], weights=[1, 4, 4])[0]))
            s.ended_at = now()
            for who in ("learner", "parent"):
                db.add(m.Event(session_id=s.id, event_type="mood_recorded", payload={"respondent": who, "phase": "post"}))
        if rng.random() < 0.25:
            db.add(m.Event(session_id=s.id, event_type="summary_shared", payload={}))

        # back-date everything for this session across the last `days` days
        t0 = start + timedelta(seconds=rng.uniform(0, days * 86400))
        s.created_at = t0
        if s.ended_at:
            s.ended_at = t0 + timedelta(minutes=rng.randint(8, 25))
        for k, msg in enumerate(db.scalars(select(m.Message).where(m.Message.session_id == s.id).order_by(m.Message.id))):
            msg.created_at = t0 + timedelta(minutes=1 + k)
        for ev in db.scalars(select(m.Event).where(m.Event.session_id == s.id)):
            ev.created_at = t0 + timedelta(minutes=rng.randint(0, 20))
            ev.payload = {**(ev.payload or {}), "simulated": True}
        for model in (m.EvidenceGap, m.AlignmentResponse, m.GuardrailLog):
            for row in db.scalars(select(model).where(model.session_id == s.id)):
                row.created_at = t0 + timedelta(minutes=rng.randint(1, 15))
        for case in db.scalars(select(m.Escalation).where(m.Escalation.session_id == s.id)):
            case.created_at = t0 + timedelta(minutes=rng.randint(2, 15))
            age_days = (now() - case.created_at).days
            case.status = rng.choices(["resolved", "in_progress", "assigned", "pending"],
                                      weights=[8, 1, 1, 1] if age_days > 7 else [1, 2, 2, 3])[0]
            if case.status != "pending":
                case.assigned_to = rng.choice(["Counsellor A", "Counsellor B", "Counsellor C"])
                case.assigned_at = case.created_at + timedelta(minutes=rng.randint(3, 90))
            if case.status == "resolved":
                case.resolved_at = case.assigned_at + timedelta(minutes=rng.randint(10, 60))
        db.commit()
        stats["sessions"] += 1
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    upgrade_to_head()
    with SessionLocal() as db:
        removed = clear_simulated(db)
        stats = simulate(db, n=args.n, seed=args.seed)
        esc = db.scalar(select(m.Escalation.id).join(m.SessionRow).where(m.SessionRow.simulated.is_(True)).limit(1))
    print(f"Removed {removed} old simulated sessions. Created {stats['sessions']} SIMULATED sessions "
          f"({stats['turns']} chat turns) — all flagged simulated=true. Escalations present: {bool(esc)}")


if __name__ == "__main__":
    main()
