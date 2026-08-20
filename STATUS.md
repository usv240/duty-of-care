# Submission status

Last verified: 2026-08-20 EDT

| Gate | State | Evidence / next action |
|---|---|---|
| Public standalone repository | Pass | `github.com/usv240/duty-of-care` |
| Apache-2.0 | Pass | Root `LICENSE` |
| Google-only AI dependency policy | Pass | Gemini on Vertex AI, Google ADK, Google Agent Search |
| Live Google runtime | Pass | Cloud Run revision `duty-of-care-agent-backend-00014-fds`; `docs/LIVE-ACCEPTANCE.json` |
| Deterministic gate + citations + human decision | Pass | Live positive and no-flag acceptance cases |
| Offline automated suite | Pass | Cloud Build `9255273e-d236-4856-9673-5bd111693419`: Ruff clean, 24 tests passed |
| Replit Agent used materially | **Pending external action** | Follow `replit.md`; preserve transcript and commit evidence |
| Public Replit deployment | **Pending external action** | Must verify signed-out `replit.app`/`replit.dev` URL |
| Qualified independent ten-fragment review | **Pending external action** | Send `evaluation/` pack; preserve credentials, consent, labels, and limitations |
| Public demo video, at most 3 minutes | **Pending external action** | Record only after Replit URL and external review evidence exist |
| Devpost submission | **Pending external action** | Complete form and retain final confirmation before deadline |

The Cloud Run URL is a functional fallback and proof of the Google agent runtime. It does not satisfy the Replit hosting requirement by itself.
