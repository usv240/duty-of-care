# Replit build evidence (TEMPLATE, not evidence)

This file is a template. Copy it to `docs/REPLIT-BUILD-EVIDENCE.md` only after
a genuine Replit Agent session and a public Replit deployment exist. Do not fill
in any line you cannot back with a transcript, screenshot, commit, or URL.

## Replit Agent

- Workspace: `<replit workspace URL>`
- Agent session date (UTC): `<YYYY-MM-DD HH:MM>`
- Prompt used: the exact prompt from `replit.md`
- Transcript reference: `<Agent history link or screenshot filenames>`
- Agent-authored commit: `<full SHA>` on `main` of `usv240/duty-of-care`
- Material changes Agent made (files, tests, docs):
  - `<file>`: `<what changed and why>`
- Tests Agent ran and their result: `<command and summary>`
- Decisions Agent explained: `<short list>`

After the commit is pushed, set on the Replit deployment and on Cloud Run:

```text
DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL=<transcript or evidence URL>
DUTY_OF_CARE_REPLIT_AGENT_COMMIT=<full SHA>
```

The Replit Agent card on `/stack` reads those two variables and nothing else.

## Replit deployment

- Public URL: `https://<app>.replit.app`
- Deployment type: Autoscale
- Secrets set on Replit: `DUTY_OF_CARE_BACKEND_URL`, `DUTY_OF_CARE_API_KEY_SECRET`,
  the two evidence variables above. No Google service-account key.
- Replit Auth: `<enabled / not enabled>` — proof: `<screenshot of /v1/me while signed in>`
- Replit Database: `<postgres / key-value / not enabled>` — proof: `<GET /v1/decisions backend field>`
- Replit App Storage: `<bucket id or not enabled>` — proof: `<POST /v1/exports backend field>`
- Scheduled Deployment: `<schedule and command python -m scripts.scheduled_recheck>` — proof: `<run log line>`

## Signed-out verification

| Check | Desktop | Mobile | Time (UTC) |
|---|---|---|---|
| `/` loads light, ribbon shows Replit tools active | | | |
| Guidance case returns cited clauses and an ADK explanation | | | |
| Responsible depiction returns zero notes | | | |
| Dismissal keeps reasoning visible | | | |
| `/developers` mints a key and runs live | | | |
| `/presets` downloads work | | | |
| `/stack` shows Replit Agent and Autoscale as active | | | |
| Crisis footer visible on every page | | | |
| `/health` reports `product_surface: replit` | | | |

## Still open

- `<anything not yet verified>`
