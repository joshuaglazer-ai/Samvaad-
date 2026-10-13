# Data dictionary

All monetary values are Indian Rupees (INR). Earnings are stored per `earnings_basis` (seed: monthly).
`data_status` is one of `verified | historical | demo | unavailable`. **All seed data is `demo`.**

## Evidence tables

### sources
| Field | Type | Meaning |
|---|---|---|
| id | int | PK |
| title | text | Shown to families as the "Source" of a figure |
| url, publisher | text | Optional provenance |
| reporting_period | text | e.g. `FY 2024-25` |
| verified_on | date text | Date a human verified the source (NULL for demo) |
| notes | text | Free text |

### trades
| Field | Type | Meaning |
|---|---|---|
| slug | text, unique | Stable ID used by tools, e.g. `electrician` |
| name_en / name_kn | text | Display names |
| sector | text | `Electrical`, `Automotive`, `Healthcare`, `Green Energy` |
| nsqf_level | int | Indicative NSQF level ("a national ladder of skill levels") |
| qualification_code, awarding_body | text NULL | **Left NULL** until verified on nqr.gov.in — never invented |
| duration_months | int | Course length |
| entry_requirement_en/kn | text | Plain-language requirement |
| entry_min_education | enum | Structured minimum (`class_8`…`graduate`) used for eligibility |
| job_roles_en/kn | JSON list | Typical first jobs |
| icon | text | Icon name used by the UI |

### providers
| Field | Meaning |
|---|---|
| name, district, state | Seed names are fictional and start with "Demo …" |
| provider_type | `government_iti`, `skill_centre`, `private_training_partner`, `imported` |
| accreditation | NULL unless known |
| data_status | Evidence status |
| trades | JSON list of trade slugs offered (SAMVAAD addition, see decisions D7) |

### outcomes
| Field | Meaning |
|---|---|
| trade_id, provider_id | provider_id NULL = aggregate across providers |
| geo_level | `district`, `state` or `national` |
| district | Set only when geo_level = district |
| year, reporting_period | Start year (2024 for FY 2024-25) and label |
| placement_numerator / denominator | Placed / certified learners |
| placement_rate | 0–100 (%) |
| earnings_min / max / median | Rupees per `earnings_basis` |
| earnings_basis | `monthly` or `annual` |
| sample_size | Learners the figure is based on |
| source_id, data_status, verified_on | Evidence trail |

### progression_steps
`trade_id, step_order, kind (job|upskill|apprenticeship|diploma|degree), title_en/kn, nsqf_level, entry_requirement_en/kn, entry_min_education, duration_months, source_id`.

### costs_support
`trade_id, district (NULL = state-wide), fee_min, fee_max, support_type (scheme|stipend|scholarship|none), description_en/kn, source_id, data_status, income_brackets` (JSON; empty = applies to all incomes). Rows with `support_type=none` carry the fee band.

## Engagement tables

### sessions
Random UUID `id`; **no names**. `language`, `district`, `income_bracket` (optional), `learner_education`,
`learner_interests` (JSON), `top_concerns` (JSON), self-reported moods `mood_pre/post_learner/parent` (1–5),
`helper_mode`, `consent_given`, `created_at`, `ended_at`, `escalated`, `simulated` (true for generated dashboard data),
`participation_mode` (`together` | `two_devices` | `learner_only`), `family_code` (4 digits, expires after 2 hours),
`family_code_expires_at`, `parent_joined_at`, `parent_language`.
**All parent data is self-identified**; `two_devices` sessions (parent joined on their own phone) are the strongest signal.

### messages
`session_id, role (user|assistant|counsellor), speaker (learner|parent|helper|bot|counsellor), text, language,
concern_category, sentiment (-2..2, model-estimated), sentiment_confidence (0..1), tool_calls (JSON),
cards (JSON shown with the reply), guardrail_status (pass|regenerated|fallback|na), device_id (random per-phone id,
no personal data), live (counsellor-room message), created_at`.

### alignment_responses
`session_id, respondent (learner|parent), device_id, ranking` (JSON list of the 5 values, most important first:
`earning_soon, near_home, respect, study_further, safety`).

### evidence_gaps
One row per data-tool call that returned `found=False`: `trade_slug, district, concern_category, tool_name, query`.

### escalations
`trigger (user_request|no_data|negative_sentiment|sensitive_topic|repeated_failure)`,
`status (pending|assigned|in_progress|resolved)`, `summary_en/kn` (3 lines), `assigned_to`, timestamps.

### callback_requests
Stored separately from sessions. `phone_encrypted` (Fernet), `preferred_time`, `consent`, `deleted_at`
(phone is wiped on delete).

### events
`event_type` (`session_started`, `outcome_viewed`, `ladder_viewed`, `alignment_completed`, `summary_shared`,
`mood_recorded`, `voice_used`, …) and JSON `payload`. Simulated sessions carry `payload.simulated = true`.

### guardrail_logs
Every guardrail trigger: `attempt`, `outcome (regenerated|fallback)`, `reply_text`, `unmatched` numbers.

## Enumerations
- **Concerns:** `income, job_security, social_status, safety, cost, distance_migration, degree_first, other`
- **Income brackets (per year, configurable):** `<1.5L, 1.5-3L, 3-6L, >6L, prefer_not_to_say`
- **Education:** `class_8, class_10, class_12, iti, diploma, graduate, other`
