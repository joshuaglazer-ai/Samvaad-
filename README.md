# SAMVAAD — Guiding Families. Empowering Futures.

**Smart India Hackathon 2026 · Problem Statement SIH26241 · Ministry of Skill Development and Entrepreneurship (MSDE) · Theme: Smart Education**

SAMVAAD is a career-guidance companion that a **learner and their parent use together**, in **English, Kannada, Hindi
or Telugu** (with voice),
to explore vocational training with **honest, sourced local data** — and reach a human counsellor when needed.
Scheme administrators get a dashboard showing **where and why parental resistance is concentrated**.

> ⚠️ **Data honesty statement.** Every outcome figure in this repository is **simulated demo data**
> (`data_status = demo`, source "SAMVAAD simulated demo dataset"), shown in the app with a visible
> **"Demo data — for testing only"** badge. The 200 dashboard sessions are **simulated families**, flagged
> `simulated = true` and labelled in the dashboard. Training-centre names all start with "Demo …". No figure here
> describes real people or real institutions. Official qualification codes are intentionally left blank until verified
> on nqr.gov.in. Organiser data can be loaded with the importer below without any redesign.

---

## How SAMVAAD meets the expected outcomes

| # | Expected outcome | What we built |
|---|---|---|
| 1 | Conversational tool for learners + parents, ≥1 regional language + English | Joint chat in **English, Kannada, Hindi and Telugu** (voice in/out per language); three ways to take part — *answer together* (side by side), *parent on their own phone* (QR + family code, own language), *learner only*; Family Alignment Cards feed the conversation; short, kind answers (reassure → one fact → next step) |
| 2 | Verified outcome-data backend | Status-tagged records (`verified / historical / demo / unavailable`), **numbers only from database tool calls**, a **numeric guardrail** that rejects any unsupported number, district → state → national fallback reported honestly, organiser-data importer |
| 3 | Admin dashboard: where and why resistance is concentrated | District map (size = sessions, colour = resistance share), concerns by district and income, model sentiment vs self-reported mood (separate), funnel, Alignment Gaps, **Evidence Gap Radar**, data quality, CSV export, small-cell suppression |
| 4 | Low-literacy, low-digital-familiarity design | Voice input and read-aloud (en/kn/hi/te-IN), picture cards, **whole journey without typing in all four languages** (tested), 18px+ text, 48px+ targets, helper mode, **Lite mode** for low-end phones, light and pure-black dark themes, WCAG AA contrast in both (tested) |
| 5 | Escalation to human counsellors | Automatic triggers (request, missing data ×2, 3 negative parent turns, sensitive topics, repeated guardrail failure), bilingual 3-line case summary, **live chat** (WebSocket + polling fallback) or **call-back** with explicit consent and encrypted, deletable phone numbers |

## Quick start (mock mode — no API key needed)

Requires Python 3.11+ and Node 20+.

```bash
git clone https://github.com/joshuaglazer-ai/Samvaad-.git && cd Samvaad-
cd backend && python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt && cp ../.env.example .env
python -m seed.seed --all && python -m seed.simulate_sessions        # demo evidence + 200 simulated sessions
uvicorn app.main:app --reload                                        # API on http://localhost:8000
# in a second terminal:
cd frontend && npm install && npm run dev                            # app on http://localhost:5173
```

The Counsellor console (`/counsellor`) and Admin dashboard (`/admin`) use the PINs in `backend/.env`
(`change-me` by default — **change them**).

### Using the real Claude API
Set in `backend/.env`:
```
LLM_MODE=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5-5        # counselling turns
ANTHROPIC_FAST_MODEL=claude-haiku-5-5    # message tagging
```
The frontend never calls the LLM; keys stay on the backend. If the key is missing, the app falls back to mock mode.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./samvaad.db` locally; PostgreSQL in deployment (`postgres://…` is normalised automatically) |
| `LLM_MODE` | `mock` (default, deterministic, still uses real data tools) or `anthropic` |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_FAST_MODEL` | Claude settings (backend only) |
| `ANTHROPIC_FALLBACKS` | Empty (default) or `default` to enable server-side refusal fallback — not yet verified with a real API call |
| `ADMIN_PIN`, `COUNSELLOR_PIN` | Demo-grade PINs for staff screens |
| `PHONE_ENCRYPTION_KEY` | Fernet key for call-back numbers (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). **Required in deployment** — without it an in-memory key is used and numbers become unreadable after a restart |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `INCOME_BRACKETS` | Income bands (configurable to match organiser data) |
| `VITE_API_BASE_URL` | Frontend → backend URL (`frontend/.env`) |

## Demo walkthrough (about 5 minutes)

1. **Landing** — a real night sky (Yale Bright Star Catalogue, as seen from Bengaluru tonight). Choose **ಕನ್ನಡ / हिन्दी / తెలుగు / English** (tap *Hear* to listen to each name), tap **Start together**. Toggle **Dark** and **Lite** in the header (Lite = no WebGL, the same sky as a still image).
2. **Onboarding** — each question is read aloud. Choose how you are taking part (**together**, **parent on own phone**, or **learner only**), then **Kalaburagi**, Class 10, interests, worries (Safety, Income), optionally income, and helper mode.
3. **Family Alignment Cards** — *together*: both rows of five cards on one screen, saved together. *Two phones*: the learner's phone shows a QR + 4-digit code; open `/join` on a second phone, choose another language, and arrange the parent's cards there. The result is gentle: "You both value … You see … differently."
4. **Mood check** — five faces each, for learner and parent.
5. **Chat (no typing)** — tap **How much can I earn?** → an **Outcome card** with placement rate, earnings range, sample size, period, data level and the **Demo data** badge. Ask about **EV** in Kalaburagi → "District data is not available; this is the state-level figure." Tap **What are the next steps?** → the **constellation career ladder**, with the steps the learner can start now glowing gold.
6. **Honest fallback** — ask "How much does a plumber earn?" → "I don't have verified data for this yet…" plus a counsellor offer, and an entry in the Evidence Gap Radar.
7. **Escalation** — open `/counsellor` in another tab (PIN), then ask "Is it safe for my daughter to travel at night?" → a case appears instantly with a bilingual summary. Use live chat between the two tabs, or request a call-back.
8. **Finish** → mood after → **Family Summary Card**, with a QR code, save as image, and share.
9. **Admin** (`/admin`) — the simulated-data banner; Kalaburagi stands out on the map (safety, income and distance worries); alignment gaps, funnel, Evidence Gap Radar, data quality and CSV export.

## Loading organiser data

```bash
cd backend
cp seed/mapping.example.yaml mapping.yaml     # edit column names to match the organiser CSV
python -m seed.import_csv --file data.csv --mapping mapping.yaml --status verified --dry-run
python -m seed.import_csv --file data.csv --mapping mapping.yaml --status verified
```
Every row is validated. Rejected rows go to `import_errors.csv` with reasons, units are converted (annual ↔ monthly,
lakh → rupees), and missing values are never guessed. Imported records outrank demo records for the same year and place.

## Tests and evaluation

```bash
cd backend && python -m pytest                 # 121 tests: data tools, guardrail (4 scripts), languages, family codes, escalation, analytics, importer, chat
python -m eval.run_eval                        # 40 questions (10 each en/kn/hi/te) → eval/results.md (generated)
cd ../frontend && npm test                     # Vitest: i18n completeness, contrast (light + dark), star maths, voice, Lite mode
npx playwright test                            # e2e: tap-only journeys in 4 languages, two-phone family, dark mode, sky, a11y, escalation, admin
```
The e2e tests expect the backend on :8000 (mock mode, seeded) and the frontend on :5173.
Latest eval: **40/40** questions pass every check in mock mode — see [backend/eval/results.md](backend/eval/results.md).

## Architecture

```
React PWA (Vite, Tailwind, R3F, Recharts, Leaflet, i18next, Web Speech)
        │  REST + WebSocket (no LLM keys in the browser)
FastAPI ── chat.py ── llm.py (Claude | deterministic mock)
   │            ├── data_tools.py   ← the ONLY place figures are queried (fallback + gap logging)
   │            ├── guardrail.py    ← every number in a reply must match this turn's tool output
   │            ├── sentiment.py    ← concern + sentiment per message
   │            └── escalation.py   ← triggers, bilingual summaries, live rooms
   ├── analytics.py (small-cell suppression)       └── SQLAlchemy + Alembic (SQLite / PostgreSQL)
```
Key rules live in [CLAUDE.md](CLAUDE.md); design choices in [docs/decisions.md](docs/decisions.md); fields in
[docs/data_dictionary.md](docs/data_dictionary.md); sources and verification TODOs in [docs/source_register.md](docs/source_register.md);
accessibility status in [docs/accessibility_checklist.md](docs/accessibility_checklist.md); deployment in [docs/deployment.md](docs/deployment.md).

## Known limitations

- **All outcome data is demo data.** Placement and earnings figures, providers, fees and ladders are simulated until organiser or official data is imported. NSQF levels and progression routes are indicative.
- **Kannada, Hindi and Telugu text is AI-written** and marked `needs_native_review` (`kn.json`, `hi.json`, `te.json`, `backend/app/lang_text.py`, trade names in `seed/reference_data.py`).
- **Parent responses are self-identified.** "Answer together" and "parent on own phone" reduce impersonation but cannot prevent it; the dashboard labels parent figures accordingly and can filter by participation mode.
- **Server-side refusal fallback is off** (`ANTHROPIC_FALLBACKS` empty) because it has not been verified with a real API call yet.
- **Not yet tested with real families.** The accessibility checklist includes a field-test template for the team.
- **Staff auth is demo-grade** (a shared PIN per role, sent as a header; also as a query parameter for WebSocket and CSV export). Replace it with real identity before any live use.
- **Voice** depends on the device: many Android phones lack Kannada or Telugu speech voices or recognisers (the app then shows a calm notice in that language and the tap options keep working). `lib/voice.ts` is ready for a server-side provider such as Bhashini.
- **Live-chat rooms are in-process**, so run one backend worker (or add Redis pub/sub to scale out). Polling keeps working either way.
- **Mock mode** answers from templates and covers the pilot's trades and concerns. Open-ended questions need `LLM_MODE=anthropic`.
- **Sentiment** in mock mode comes from keywords and is approximate. The dashboard labels it as a model estimate, separate from self-reported mood.
- Lighthouse mobile scores have not yet been measured on a deployed build (target ≥ 80 in Lite mode).

## Credits

- **Star data:** Yale Bright Star Catalogue, 5th revised edition — D. Hoffleit & W. H. Warren Jr. (1991), public domain,
  obtained from CDS Strasbourg (catalogue V/50). Processed at build time by `frontend/scripts/build-stars.mts`
  (`npm run build:stars`) into 4,103 stars (V ≤ 5.8). The faint Milky Way band is a procedural texture laid along the
  real galactic plane.
- **Map tiles:** © OpenStreetMap contributors.
- **Fonts:** Plus Jakarta Sans, Noto Sans Kannada (Google Fonts, SIL Open Font License).

---
*SAMVAAD offers guidance, not guarantees. The final decision is always yours.*
