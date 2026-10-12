# SAMVAAD — project rules for Claude Code

SAMVAAD ("Guiding Families. Empowering Futures.") is a family career-guidance platform for vocational
training (SIH 2026, PS SIH26241, MSDE). Learners **and** parents use it together, in Kannada or English.
Pilot: Karnataka — Bengaluru Urban, Mysuru, Kalaburagi, Dharwad; sectors Electrical, Automotive,
Healthcare, Green Energy; ~8 trades.

Layout: `backend/` (FastAPI + SQLAlchemy + Anthropic SDK), `frontend/` (React + Vite + Tailwind), `docs/`.
Decisions go in `docs/decisions.md`. Data fields in `docs/data_dictionary.md`. Sources in `docs/source_register.md`.

## Non-negotiable rules
1. **The LLM only narrates. Numbers come from database tool calls** (`backend/app/data_tools.py` is the only
   place outcome figures are queried). The model never states a statistic not present in a tool result that turn.
2. **Numeric guardrail** (`guardrail.py`): every number in a reply (Western + Kannada numerals, ₹, %, lakh/ಲಕ್ಷ)
   must match a tool-output value. Fail → regenerate once with a correction note → fail again → safe fallback +
   counsellor offer. Log every trigger. Small integers ≤ 10 used as counts/steps are allowed.
3. **Every displayed figure shows its evidence**: source, period, sample size, geo level, data-status badge.
4. **Data status** on every outcome record: `verified | historical | demo | unavailable`. Seed data is `demo`
   and must be visibly labelled "Demo data". Never present demo/simulated data as real.
5. **Honest fallback**: no data → say so, log an evidence gap, offer a counsellor. State-level only → say
   "District data is not available; showing the state figure."
6. **Neutral counselling**: present options, never pressure, never call a path inferior. A degree may be better.
7. **Privacy**: no names, random session UUIDs, phone only on callback opt-in (encrypted, separate table,
   deletable). One-line consent notice at onboarding (DPDP Act).
8. **Secrets** only in `.env`, read by the backend. The frontend never calls the LLM.
9. **Kannada** UI strings live in `frontend/src/i18n/kn.json` with `"_review_status": "needs_native_review"`.
   Natural Kannada, not word-for-word.
10. App must run fully with `LLM_MODE=mock` (no API key). Mock still calls real data tools.
11. Do not add: vector DBs, fine-tuning, multi-agent frameworks, LangChain, WhatsApp, user accounts.

## Answer shape (Update 2)
Max ~50 words, 2–3 short sentences, one idea: (1) reassure — one warm, varied line; (2) one simple fact from the
tool result in everyday words, amounts rounded with "about" (nearest ₹500/₹1,000, see guardrail.py; exact figures
stay on the card); (3) one gentle next step. Never "guaranteed", "surely", "definitely", "100%". Kind no-data line:
"I don't have reliable data on this yet. A counsellor can help — would you like that?"

## Tone
Minimal, simple, warm, professional. Short sentences, everyday words. Acknowledge before answering
("That is an important question."). Never use: backward, convince, low-status, uneducated, only a trade,
you are wrong, just, simply — or anything judging family/caste/community/gender/religion/region/income.
No gender-role assumptions; safety answers factual and calm. NSQF = "a national ladder of skill levels".
End every bot turn with one gentle next step (question or option button).
Disclaimer (once per session + footer): "SAMVAAD offers guidance, not guarantees. The final decision is always yours."

## Copy samples
- Greeting: "Welcome. Let's explore career options together, at your pace."
- Acknowledge: "That is an important question. Here is what the data shows."
- No data: "I don't have verified data for this yet. A counsellor can help you with it. Would you like to talk to one?"
- State fallback: "District data is not available. This is the state-level figure."
- Demo label: "Demo data — for testing only."
- Disagreement: "You both want what is best. You see Studying further a little differently. Let's look at both views."
- Closing: "Thank you for exploring with SAMVAAD. The final decision is always yours."

## Commands
- Backend: `cd backend && .venv/Scripts/python -m pytest` · run `uvicorn app.main:app --reload`
- Seed: `python -m seed.seed && python -m seed.simulate_sessions`
- Frontend: `cd frontend && npm run dev` · `npm test` · `npm run build`
