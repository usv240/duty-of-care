# Submission status

Last verified: 2026-09-04 (see `docs/AUDIT-2026-09-04.md` and `docs/LIVE-ACCEPTANCE.json`)

| Gate | State | Evidence / next action |
|---|---|---|
| Public standalone repository | Pass | `github.com/usv240/duty-of-care` |
| Apache-2.0 | Pass | Root `LICENSE`, `NOTICE`, `ASSET_RIGHTS.md` |
| Google-only AI dependency policy | Pass | Gemini on Vertex AI through Google ADK, Google Agent Search; no other AI dependency |
| Live Google runtime | Pass | Cloud Run `duty-of-care-agent-backend` revision `00020-2wj`, one warm instance; probes in `docs/LIVE-ACCEPTANCE.json` |
| Managed agent on Vertex AI Agent Engine | Pass | `duty-of-care-guidance-reviewer`; `meta.agent_runtime` on live reviews; `/stack` |
| Model Armor on agent output | Pass | template `duty-of-care-agent-output`; `model_armor_clear` in `meta.gate` |
| Corpus across five jurisdictions | Pass | 36 clauses (WHO, Samaritans, National Action Alliance, Mindframe, Mindset); `/v1/guidance` |
| Live-pipeline evaluation published | Pass | `docs/EVAL-LIVE.json`: 30/30 candidate scenes grounded, 0 clauses outside jurisdiction, 63/63 notes structured, 0 withheld, p50 9.5 s; served in `/v1/eval/latest` |
| Independent judge of agent answers | Pass | Vertex AI Gen AI Evaluation Service: 9/9 notes grounded (mean 1.0), 9/9 safe (mean 1.0), 2026-09-08; `docs/EVAL-GROUNDEDNESS.json`; served in `/v1/eval/latest` |
| Research evidence base, verified and retrieved per note | Pass | 14 records checked against Europe PMC; second Agent Search store `duty-of-care-evidence`; `/evidence`, `/v1/evidence`, `docs/EVIDENCE.md` |
| Uptime monitoring | Pass | Cloud Monitoring check `duty-of-care-health`, 5-minute period, content match |
| Streaming progress on the workbench | Pass | `POST /v1/review/stream` |
| Deterministic gate + citations + human decision | Pass | Live guidance case: three grounded notes including the document-level signpost note; responsible depiction: zero candidates |
| Demo presets viewable and downloadable | Pass | `/presets`, `/v1/presets/{id}/download` (fountain, txt, json) |
| Bring-your-own draft | Pass | Browser-side Fountain/text/Markdown/FDX import; nothing stored |
| Public API with one-click keys and live run | Pass | `/developers`, `POST /v1/keys`, `meta.gate`, Markdown report; signing secret in Secret Manager |
| Sponsor stack visible on every page | Pass | Ribbon on all pages, `/stack`, `/v1/stack` with earned statuses |
| Offline automated suite | Pass | 54 tests, Ruff clean, Playwright page check across five pages at two widths (2026-09-08, local; CI runs the same) |
| Replit Agent used materially | Pass | Agent commits `21d70ef`, `077ca7e` (2026-09-05) built the allowlisted backend proxy and tests; `docs/REPLIT-BUILD-EVIDENCE.md`; `/stack` shows Replit Agent active |
| Public Replit deployment | Pass | https://duty-of-care.replit.app (Autoscale), verified signed-out 2026-09-08 at desktop and phone widths; pull and republish pending for the Evidence page and self-reported stack |
| Replit Auth, Database, App Storage, Scheduled Deployment live | **Pending owner activation** | Adapters and Agent-written tests exist; enable in the workspace, then verify via `/v1/me`, `/v1/decisions`, `/v1/exports`, `/stack` |
| Qualified independent ten-fragment review | **Pending external action** | Send `evaluation/` pack; `/v1/eval/latest` reports it as pending |
| Public demo video, at most 3 minutes | **Pending external action** | Record only after Replit URL and evidence exist |
| Devpost submission | **Pending external action** | Complete form before 2026-09-09 14:00 PT |

The Cloud Run URL is the Google agent backend and a functional fallback. It does not satisfy the Replit hosting requirement by itself.
