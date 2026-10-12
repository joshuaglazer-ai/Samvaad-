# Accessibility & low-literacy checklist (PS Outcome 4)

Status key: ✅ done and verified · 🟡 done, needs real-user validation · ⬜ not yet

## Automated verification
- `frontend/src/lib/contrast.test.ts` — every text/background token pair used in the UI checked against WCAG AA (4.5:1).
- `frontend/e2e/a11y.spec.ts` — axe-core WCAG 2.1 A/AA scan of Landing, Kannada onboarding, and Chat with cards: **0 serious/critical violations**.
- `frontend/e2e/journey.spec.ts` — the full journey in English **and** Kannada completed **using taps only** (no typing); Lite mode renders **no WebGL canvas**.

## Contrast (measured)
| Pair | Ratio | AA |
|---|---|---|
| ink-900 on lavender-50 (body) | 14.62 | ✅ |
| ink-900 on sky-200 (page bottom) | 11.45 | ✅ |
| ink-600 on sky-200 (secondary text) | 6.25 | ✅ |
| ink-600 on lavender-100 | 7.27 | ✅ |
| white on primary-600 (buttons, user bubbles) | 5.93 | ✅ |
| white on primary-700 (hover) / primary-700 on white (links) | 8.46 | ✅ |
| white on success-600 (Verified badge) | 5.25 | ✅ |
| white on warning-600 (Historical badge) | 5.00 | ✅ |
| white on info-600 (Demo badge) | 6.41 | ✅ |
| white on ink-600 (Unavailable badge) | 8.60 | ✅ |
| ink-900 on star highlight | 14.23 | ✅ |
`lavender-300` and `lavender-500` are decorative only; no text is placed on them.

## Checklist
| # | Item | Status | Where |
|---|---|---|---|
| 1 | Body text ≥ 18px (root font 18px); chat bubbles 20px | ✅ | `styles/index.css`, `MessageBubble` |
| 2 | Tap targets ≥ 48×48px (all buttons `min-h-12` = 54px) | ✅ | `Button`, `IconCard`, chips |
| 3 | Every action is icon **plus** text label; no icon-only buttons | ✅ | `Button` API requires children |
| 4 | Whole journey possible without typing (picture cards, quick replies, voice) | ✅ | e2e journey test |
| 5 | Each onboarding question auto-read aloud; toggle visible | ✅ | `Onboarding` + `useSpeak` |
| 6 | Speaker button on every bot message + auto-read toggle in chat | ✅ | `MessageBubble`, `Chat` |
| 7 | No Kannada voice → visible notice + text highlighted (no silent failure) | ✅ | `VoiceMissingNotice`, `.reading-highlight` |
| 8 | Mic hidden gracefully where unsupported, with an explanation | ✅ | `MicButton` |
| 9 | Language switch visible on every screen; session kept | ✅ | `Header` (PATCH /api/session) |
| 10 | Helper mode: helper tips, slower auto-advance, `speaker=helper` messages | ✅ | `Onboarding`, `Chat`, `SpeakerToggle` |
| 11 | Data status shown by colour **and** icon **and** text | ✅ | `EvidenceBadge` |
| 12 | Visible keyboard focus ring (3px primary-700) | ✅ | `:focus-visible` |
| 13 | Radio/checkbox semantics on picture cards; labelled groups | ✅ | `IconCard`, `MoodCheck` |
| 14 | `lang` attribute follows the UI language (screen readers, fonts) | ✅ | `i18n/index.ts` |
| 15 | Reduced motion respected; Lite mode disables WebGL, blur and animation | ✅ | `device.ts`, `index.css` |
| 16 | Lite mode auto-on for ≤2 GB RAM, ≤4 cores, data saver, 2g/3g, reduced motion, no WebGL; manual toggle | ✅ | `device.ts` + unit tests |
| 17 | Live regions for new chat messages and status messages | ✅ | `aria-live` in `Chat`, `EscalationPanel` |
| 18 | Consent notice in one plain line, read aloud | ✅ | Onboarding step 2 |
| 19 | Kannada copy reviewed by a native speaker | ⬜ | `kn.json` is marked `needs_native_review` |
| 20 | Tested with real rural/semi-urban families (see template below) | ⬜ | team to complete |
| 21 | Lighthouse mobile performance ≥ 80 in Lite mode | 🟡 | run on deployed build; see README |
| 22 | Screen-reader walkthrough (TalkBack, Kannada) | 🟡 | structure passes axe; needs manual pass |

## Real-user test notes (template — to be filled by the team)

> Copy this block once per family session. Do not record names or phone numbers.

```
Date:                     Location (district / village or ward):
Facilitator:              Device (model, Android version, network):
Who took part:            [ ] learner  [ ] parent  [ ] helper    Language used: [ ] ಕನ್ನಡ [ ] English
Reading comfort (self-described): [ ] reads easily [ ] reads slowly [ ] prefers listening
Lite mode on?  [ ] auto  [ ] manual  [ ] off

Tasks (✓ done alone · ~ done with help · ✗ could not)
  [ ] Start together and choose language
  [ ] Answer onboarding questions using pictures
  [ ] Arrange alignment cards (learner)        [ ] (parent)
  [ ] Ask a question by voice                  [ ] by quick reply
  [ ] Understand the earnings card (ask: "What does this card say?")
  [ ] Understand the "Demo data" badge
  [ ] Understand the career ladder
  [ ] Find "Talk to a counsellor"
  [ ] Open / save / share the Family Summary

Mood before (learner/parent):      Mood after (learner/parent):
What confused them (quote their words):
Words they did not understand:
What reassured the parent:
Kannada wording issues spotted:
Bugs / slow screens:
Changes we will make:
```
