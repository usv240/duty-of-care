# Replit track handoff

This file is intentionally honest: **Replit Agent evidence and the public Replit deployment are pending.** A local or Cloud Run build cannot substitute for the sponsor's required workflow.

## Owner procedure

1. In an authenticated Replit account, import `https://github.com/usv240/duty-of-care` as a new app.
2. Open Replit Agent and paste the prompt below. Let Agent inspect, plan, edit, test, and explain its work; do not manually paste prewritten files into the workspace.
3. Review the diff. The Agent change must be material and remain in the final repository.
4. Commit and push that change to this public repository with an Agent-authored build record in `docs/REPLIT-BUILD-EVIDENCE.md`.
5. Publish with Replit Autoscale. Set `DUTY_OF_CARE_BACKEND_URL` to `https://duty-of-care-agent-backend-109051079423.us-central1.run.app`; do not store a Google service-account key in Replit.
6. Verify the public `replit.app` or `replit.dev` URL in a signed-out browser: landing page, both samples, source links, dismissal reasoning, fixed crisis footer, mobile layout, and `/health`.
7. Record the final URL, UTC verification time, deployment type, Agent transcript link or screenshots, and the pushed commit SHA in the evidence file.

## Exact Replit Agent prompt

> Inspect this repository and its README, tests, and safety boundaries. Build a production Replit product surface for Duty of Care without weakening the existing deterministic gates or Google ADK/Agent Search backend. The Replit surface must proxy only the allowlisted backend routes `/health`, `/v1/resources`, `/v1/guidance`, `/v1/samples`, and `/v1/review` to the fixed `DUTY_OF_CARE_BACKEND_URL`; it must never accept an arbitrary upstream URL and must enforce body/time limits. Use Replit Auth for optional saved review decisions, Replit Database for the writer's accept/dismiss/expert-review state and reasoning, and Object Storage only for an explicit user-requested JSON export. Store no screenplay by default. Add a scheduled health check that records only uptime metadata. Keep anonymous demo access, the light default, Plain/Technical toggle, fixed crisis resources, exact source links, and a visible statement that the writer decides. Add tests, update the architecture and privacy documentation, run them, and explain every material decision. Do not claim clinical safety, compliance, certification, expert validation, or completion of any service you did not actually configure.

## Evidence template

`docs/REPLIT-BUILD-EVIDENCE.md` must contain:

- public deployment URL;
- Replit Agent transcript/screenshot references;
- Agent-generated commit SHA and summary of material changes;
- Replit Auth, Database, Object Storage, Scheduled Deployment, and Autoscale status with proof;
- signed-out browser verification results and timestamp;
- any limitation still open.

Do not mark the Replit requirement passed until every mandatory track item in `Rules.md` and the public deployment have been independently checked.
