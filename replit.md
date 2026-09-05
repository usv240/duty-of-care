# Replit track handoff

This file is intentionally honest: **Replit Agent evidence and the public Replit deployment are pending.** A local or Cloud Run build cannot substitute for the sponsor's required workflow. Until both exist, `/stack` shows Replit Agent and Autoscale as `pending` and `/health` reports `product_surface: cloud_run_fallback`.

## What is already in the repository for Replit

- `.replit`: Autoscale deployment of this same FastAPI app, port 8080, Python 3.11 module.
- `duty_of_care/replit_platform.py`: runtime detection (`REPL_ID`, `REPLIT_DEPLOYMENT`, `REPLIT_DOMAINS`), Replit Auth identity from the `X-Replit-User-*` headers (trusted only on Replit), a decision store that uses Replit Database (Postgres via `DATABASE_URL`, or the key-value store via `REPLIT_DB_URL`) with a local fallback, an export store on App Storage with a local fallback, and the scheduled re-check record.
- `scripts/scheduled_recheck.py`: the Scheduled Deployment job.
- Routes that light up on Replit: `/v1/me`, `/v1/decisions`, `/v1/exports`, and the Replit cards on `/stack`.
- `docs/REPLIT-BUILD-EVIDENCE.template.md`: the evidence file to fill in, and nothing else.
- The Google-only variables (`AGENT_ENGINE_RESOURCE`, `MODEL_ARMOR_TEMPLATE`, `VERTEX_SEARCH_DATA_STORE`) belong to the Cloud Run backend, not to Replit. When `VERTEX_SEARCH_DATA_STORE` is absent on Replit, middleware proxies only exact allowlisted route-and-method pairs to the fixed HTTPS origin in `DUTY_OF_CARE_BACKEND_URL`: `GET /health`, `/v1/resources`, `/v1/guidance`, `/v1/presets`, `/v1/samples`, `/v1/eval/latest`, and `/v1/stack`; and `POST /v1/review`, `/v1/review/stream`, `/v1/report`, and `/v1/keys`. The request cannot choose an upstream; redirects are rejected; request and response sizes and upstream time are bounded.
- Replit Auth headers terminate on this surface for `/v1/me` and writer-scoped decision routes. Anonymous pages and review remain available. When platform services are present, `DATABASE_URL` selects managed Postgres for decision metadata and the Replit App Storage client stores explicit exports; tests exercise both selections and round trips. Neither path stores screenplay text by default.

## Owner procedure

1. In an authenticated Replit account, import `https://github.com/usv240/duty-of-care` as a new app.
2. Open Replit Agent and paste the prompt below. Let Agent inspect, plan, edit, test, and explain its work; do not paste prewritten files into the workspace.
3. Review the diff. The Agent change must be material and remain in the final repository.
4. Commit and push that change to this public repository. Copy `docs/REPLIT-BUILD-EVIDENCE.template.md` to `docs/REPLIT-BUILD-EVIDENCE.md` and fill only what you can back with the transcript.
5. Add Replit Secrets: `DUTY_OF_CARE_BACKEND_URL=https://duty-of-care-agent-backend-109051079423.us-central1.run.app`, `DUTY_OF_CARE_API_KEY_SECRET` (a fresh random string; do not reuse the Google one), and after step 4 `DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL` and `DUTY_OF_CARE_REPLIT_AGENT_COMMIT`. Never store a Google service-account key in Replit.
6. Enable Replit Auth, Replit Database, and App Storage in the workspace; create a Scheduled Deployment running `python -m scripts.scheduled_recheck` nightly.
7. Publish with Autoscale. Set the same two evidence variables on the Cloud Run service so both surfaces agree.
8. Verify the public `replit.app` or `replit.dev` URL in a signed-out browser on desktop and mobile: all four pages, ribbon showing Replit tools active, both contrast presets, source links, dismissal reasoning, `/developers` mint and live run, downloads, crisis footer, and `/health`.
9. Record the final URL, UTC verification time, deployment type, Agent transcript link or screenshots, and the pushed commit SHA in the evidence file.

## Exact Replit Agent prompt

> Inspect this repository: README.md, docs/API.md, docs/AUDIT-2026-09-04.md, replit.md, the tests, and the safety boundaries in SECURITY.md. The FastAPI app already serves the product and API and already contains Replit adapters in duty_of_care/replit_platform.py with local fallbacks. Your job is to make the Replit surface production-ready on this platform without weakening the deterministic gates or the Google ADK/Agent Search backend. Specifically: (1) make the app proxy only the allowlisted backend routes /health, /v1/resources, /v1/guidance, /v1/presets, /v1/samples, /v1/review, /v1/report, /v1/eval/latest, /v1/stack, and /v1/keys to the fixed DUTY_OF_CARE_BACKEND_URL when Google credentials are absent on Replit, never accepting an arbitrary upstream URL and enforcing body and time limits; (2) wire Replit Auth so a signed-in writer's identity reaches replit_platform.identity_from_headers, keeping anonymous review fully working; (3) confirm Replit Database backs the decision store and App Storage backs the export store, and add a test for each on this platform; (4) configure the Scheduled Deployment for python -m scripts.scheduled_recheck; (5) keep the light default, Plain/Technical toggle, fixed crisis footer, exact source links, the visible statement that the writer decides, and every page's sponsor-stack ribbon. Store no screenplay text by default. Add tests, run them, update replit.md and SECURITY.md with what you actually configured, and explain every material decision. Do not claim clinical safety, compliance, certification, expert validation, or completion of any service you did not actually configure.

## Evidence template

`docs/REPLIT-BUILD-EVIDENCE.md` must contain:

- public deployment URL;
- Replit Agent transcript/screenshot references;
- Agent-generated commit SHA and summary of material changes;
- Replit Auth, Database, App Storage, Scheduled Deployment, and Autoscale status with proof from `/v1/me`, `/v1/decisions`, `/v1/exports`, and `/stack`;
- signed-out browser verification results and timestamp;
- any limitation still open.

Do not mark the Replit requirement passed until every mandatory track item in `Rules.md` and the public deployment have been independently checked.
