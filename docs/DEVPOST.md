# Devpost entry draft — Duty of Care (Replit track)

Replace every bracketed item with verified evidence or delete the sentence. Do not submit with a bracket left in.

## Tagline

Put published sensitive-storytelling guidance beside the scene, without turning AI into a censor.

## Inspiration

Studios hire a consultant to check how a script depicts suicide. Everyone else guesses. WHO, Samaritans, the National Action Alliance, Mindframe, and others publish specific, checkable guidance for stage and screen, and most independent writers have never seen it. Samaritans' Media Advice team reviews scripts by hand; that service will never have capacity for every student film. Duty of Care exists to reach the writers it cannot, and to route them toward it when a human view is warranted.

## What it does

A writer pastes a scene, uploads a draft (Fountain, text, Markdown, or Final Draft), or loads one of six self-authored demo drafts. Three layers run, and the page shows each one working:

1. Deterministic code parses scenes and selects candidates, showing the exact phrase and rule.
2. Google Agent Search retrieves applicable, versioned clauses from a 36-clause corpus across five jurisdictions; code filters by jurisdiction and trigger class, and different jurisdictions are shown side by side, never merged.
3. A Google ADK agent on Gemini, bound to that scene through session state, explains only the retrieved clauses and drafts one alternative that keeps the drama. It must run the project's hard filter as a tool before answering; the API runs the filter again; Google Cloud Model Armor screens the result.

The writer accepts, dismisses, or asks for expert review. Dismissal keeps the reasoning visible. There is no overall score and no blocking path. Crisis resources are on every page before any interaction.

The same review is a public API: a one-click stateless key, `meta.gate` on every response naming the thresholds that passed and failed, a streaming variant that reports each layer's progress, Markdown reports, and a required `disclaimer` field an integrator cannot strip.

## How we built it

- **Google Cloud:** Gemini on Vertex AI through Google ADK with explicit safety settings; the identical agent deployed to Vertex AI Agent Engine and called over HTTP, with in-process ADK as the recorded fallback; Google Agent Search (Discovery Engine) as the only source of guidance text; Model Armor on the agent's output; Cloud Run; Secret Manager for the key-signing secret; Cloud Build; Cloud Logging with content-free traces.
- **Replit:** `[Replit Agent built …; commit …]`; Autoscale deployment at `[REPLIT_URL]`; `[Replit Auth / Database / App Storage / Scheduled Deployment: list only what is verified]`.
- **Plain code:** FastAPI, regular-expression triggers and filters, a Playwright page check in CI, 53 offline tests.

## Challenges

The hard part was restraint. The model must never be the reason a note exists, never rewrite a scene into something more specific than the writer wrote, and never say a scene is safe. That meant a gate in code (no citation, no flag), a filter the agent has to pass as a tool and then pass again, and a managed screen after both. It also meant refusing to give a score.

## Accomplishments

- A concerning draft and a conforming draft on the same subject produce three notes and zero notes respectively, live, from the same pipeline.
- The deterministic layer scores precision 1.0, recall 1.0, false-flag rate 0.0 on 48 CC0 engineering cases, served from the same endpoint that computed it.
- The live pipeline evaluation over 54 cases: 30 of 30 candidate scenes grounded, 0 clauses outside jurisdiction, 63 of 63 notes structured, 0 withheld by the filter or by Model Armor, p50 9.5 s (`docs/EVAL-LIVE.json`).
- `[Independent reviewer findings, if obtained, with limitations.]`

## What we learned

The useful role for AI here is contextual explanation after retrieval and deterministic applicability checks, not deciding whether art is acceptable. Preserving writer agency and stating contested evidence honestly are product features, not disclaimers.

## What's next

Expert review of the blinded ten-fragment pack, more jurisdictions in the corpus, and the Replit surface's saved-decision history so a writer can see what changed when the guidance corpus changes.

## Built with

google-adk, google-genai, Vertex AI Agent Engine, Google Agent Search, Model Armor, Cloud Run, Secret Manager, Cloud Build, Cloud Logging, Replit Agent, Replit Autoscale, `[Replit Auth, Replit Database, App Storage, Scheduled Deployment as verified]`, FastAPI, Playwright, pytest.

## Links

- Hosted project: `[REPLIT_URL]` (Google agent backend: https://duty-of-care-agent-backend-109051079423.us-central1.run.app)
- Repository: https://github.com/usv240/duty-of-care (Apache-2.0)
- Video: `[YouTube URL, under 3:00, public]`
