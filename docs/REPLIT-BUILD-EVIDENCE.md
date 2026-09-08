# Replit build evidence

Filled 2026-09-08 from the owner's session driving the official Replit MCP
server (`https://replit-mcp.com/server/mcp`). Every line below is backed by the
workspace git log, an Agent answer, a Cloud Run revision, or an HTTP response.
Lines that could not be backed say so explicitly. **The Replit requirement is
not passed**: the Agent build exists, but the public deployment does not yet.

## Replit Agent

- Workspace: `https://replit.com/@ujwal240/duty-of-care`
  (replId `e7596773-2a05-43c4-ab36-66dd4696592d`, Personal workspace, imported
  from `https://github.com/usv240/duty-of-care` at commit `618d450b`)
- Agent session dates (UTC):
  - `2026-09-05 05:34-05:56` — the build session. Two Agent checkpoint commits
    (below). This is the session that made the material changes.
  - `2026-09-08 ~22:20-22:33` — the same prompt sent once more through the MCP
    tool `update_app_using_prompt` (turn `01a07023-8445-77bf-b5d5-f5ff01440a6c`).
    Agent reported "Finished; passed completion validation; working tree clean".
    It re-ran the test suite and made **no file changes and no new commit**.
- Prompt used: the exact prompt from `replit.md`, verbatim, both times.
- Transcript reference: the Agent conversation pane of the workspace URL above.
  No screenshots were captured during the MCP-driven session.
- Agent-authored commits in the workspace git, on top of the imported
  `618d450b36c0263f9737f214389bef8cbb0609e9` (`git log --date=iso-strict`):
  - `21d70efc45c00b86312d98a725fc4c3e63c877ef` — `2026-09-05T05:34:27Z` —
    "Update Replit configuration"
  - `077ca7e87a39ce65a1d03cd7cf3d83cc26ce510d` — `2026-09-05T05:56:08Z` —
    "Implement backend proxy module and update environment configuration" (HEAD)
- **Not yet on GitHub.** As of 2026-09-08 22:30 UTC `origin/main` of
  `usv240/duty-of-care` is still `618d450b`. The MCP server cannot push; the
  owner must push from the workspace Git pane so the SHA above lands on `main`.
- Material changes Agent made (`git diff --stat 618d450b..HEAD`: 10 files,
  +571 / -7):
  - `duty_of_care/backend_proxy.py` (new, 273 lines): proxy to the fixed
    `DUTY_OF_CARE_BACKEND_URL`, active only when `REPL_ID` is set, the backend
    URL is set, and `VERTEX_SEARCH_DATA_STORE` is absent. Exact
    route-and-method allowlist: `GET /health`, `/v1/resources`, `/v1/guidance`,
    `/v1/presets`, `/v1/samples`, `/v1/eval/latest`, `/v1/stack`; `POST
    /v1/review`, `/v1/review/stream`, `/v1/report`, `/v1/keys`. The upstream
    must be a bare HTTPS origin (no credentials, path, query, or fragment) or
    the proxy fails closed with `503 backend_proxy_not_configured`. Redirects
    are rejected (`502 backend_redirect_rejected`). Limits: 2 MB request body
    (`413 request_too_large`), 10 MB response (`502
    backend_response_too_large`), 5 s connect / 90 s read / 120 s total (`504
    backend_timeout`). Streamed reviews that exceed size or time end with an
    explicit NDJSON `error` event. Forwarded request headers are limited to
    `accept`, `authorization`, `content-type`, `x-api-key`; response headers
    to `cache-control`, `content-disposition`, `content-encoding`,
    `content-type`. `Accept-Encoding: identity` is forced upstream.
  - `duty_of_care/main.py` (8 lines): imports `backend_proxy` and registers an
    `@app.middleware("http")` hook `_fixed_backend_proxy` that returns the
    proxied response or falls through to the local route. `/v1/me`,
    `/v1/decisions`, `/v1/exports` always stay local.
  - `tests/test_backend_proxy.py` (new, 190 lines, 9 tests): exact allowlist
    and fixed origin; stream proxied without unsafe headers; gzip-compressed
    buffered response stays usable; oversized request rejected before any
    network call; non-allowlisted method stays local; invalid backend origin
    fails closed; backend redirect not followed; oversized stream and
    timed-out stream each end with an explicit error event.
  - `tests/test_replit_platform.py` (+49): two new platform tests —
    `test_replit_database_backend_is_selected_and_round_trips` (`DATABASE_URL`
    selects `PostgresDecisionStore`, backend `replit_postgres`) and
    `test_replit_app_storage_backend_is_selected_and_round_trips`
    (`replit.object_storage.Client` selected, backend `replit_app_storage`).
  - `tests/conftest.py` (+10): autouse fixture clears
    `DUTY_OF_CARE_API_KEY_SECRET`, `DUTY_OF_CARE_BACKEND_URL`, `REPL_ID`, and
    `VERTEX_SEARCH_DATA_STORE` so unit tests never inherit workspace secrets.
  - `pyproject.toml` (+5): `httpx>=0.28,<0.29` as a runtime dependency; a
    `dev` extra with `pytest` and `ruff`; `requires-python >=3.11`; Ruff
    target `py311`.
  - `requirements.txt` (+1): `httpx>=0.28,<0.29`.
  - `.replit` (+34): modules `python-3.11`, `web`, `nodejs-20`; Nix channel
    `stable-25_05` with `libxcrypt` and `postgresql`; a development workflow
    "Start application" running Uvicorn on port 5000 with a webview; the
    Autoscale `[deployment]` block is unchanged.
  - `replit.md` (+5): documents the proxy allowlist and limits, Replit Auth
    header termination, and Postgres / App Storage selection; notes Python 3.11.
  - `SECURITY.md` (+3): the proxy boundary bullet (2 MB / 10 MB / 120 s,
    redirects rejected) and the note that the proxy enforces raw-byte and
    timeout limits before forwarding.
- Tests Agent ran and their result (as reported by Agent on 2026-09-08; not
  re-run independently from outside the workspace): `python -m pytest -q` —
  64 passed, four third-party deprecation warnings, no failures;
  `python -m ruff check .` — passed; `git diff --check` — passed.
- Decisions Agent explained: proxy only exact route-and-method pairs
  including `/v1/review/stream`; treat the backend as a fixed origin and
  reject anything that lets a request choose or alter it; bound bytes and time
  and end streams with a typed error rather than a silently truncated success;
  force identity encoding to keep byte limits honest; keep identity and
  persistence endpoints local and trust `X-Replit-User-*` only on Replit;
  store a scene fingerprint, never screenplay text; isolate tests from live
  secrets; preserve the light default, Plain/Technical toggle, crisis footer,
  source links, "the writer decides" language, and the sponsor-stack ribbon;
  do **not** claim Replit Auth, managed Database, App Storage, the nightly
  Scheduled Deployment, or publishing as active, because Agent did not
  activate those services.

Evidence variables:

```text
DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL=https://replit.com/@ujwal240/duty-of-care
DUTY_OF_CARE_REPLIT_AGENT_COMMIT=077ca7e87a39ce65a1d03cd7cf3d83cc26ce510d
```

- Cloud Run: set 2026-09-08 on `duty-of-care-agent-backend` (us-central1,
  project `agentic-fleet-2026`) via `gcloud run services update
  --update-env-vars`; serving revision `duty-of-care-agent-backend-00022-z4w`.
  Proof: `GET /health` returns `replit_platform.agent_evidence.present: true`
  with the URL and SHA above; `GET /v1/stack` reports `replit_agent: active`
  with evidence "Agent-authored commit 077ca7e87a39 with transcript evidence".
- Replit: **not yet set**. The MCP server cannot manage Replit Secrets; the
  owner must add both in the workspace Secrets pane.

## Replit deployment

- Public URL: **none yet.** `publish_app` through the MCP server on 2026-09-08
  returned: "Publishing this type of app from chat is not supported yet. Open
  the app on the Replit website and publish it there the first time; after
  that, publish_app can republish it from chat." `get_publish_status` returns
  `found: false`.
- Deployment type: Autoscale is declared in `.replit`
  (`deploymentTarget = "autoscale"`, Uvicorn on `$PORT`); no deployment exists.
- Secrets set on Replit: `DUTY_OF_CARE_BACKEND_URL` and
  `DUTY_OF_CARE_API_KEY_SECRET` were added by the owner on 2026-09-08
  (owner's own record; not verifiable through the MCP server). The two
  evidence variables are not yet set on Replit. No Google service-account key.
- Replit Auth: not verified — code path and tests exist; no `/v1/me` proof
  while signed in.
- Replit Database: not verified — adapter and selection test exist; no
  `GET /v1/decisions` `backend` field from the deployed app.
- Replit App Storage: not verified — adapter and selection test exist; no
  `POST /v1/exports` `backend` field from the deployed app.
- Scheduled Deployment: not created. Agent explicitly did not claim it.
  Command when created: `python -m scripts.scheduled_recheck`, nightly.

## Signed-out verification

Not run: there is no public URL yet. Every cell stays empty until the first
publish from the Replit website.

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

- First publish (Autoscale) from the Replit website; afterwards
  `publish_app` can republish from chat.
- Push the workspace commits (`21d70efc`, `077ca7e8`) from the Replit Git pane
  to `main` of `usv240/duty-of-care` so the recorded SHA exists on GitHub.
- Add `DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL` and
  `DUTY_OF_CARE_REPLIT_AGENT_COMMIT` as Replit Secrets so `/stack` on the
  Replit surface agrees with Cloud Run.
- Enable Replit Auth, Replit Database (Postgres), and App Storage in the
  workspace; create the nightly Scheduled Deployment.
- Run the signed-out desktop and mobile verification table and record proof
  from `/v1/me`, `/v1/decisions`, `/v1/exports`, and `/stack`.
- Independently re-run the test suite outside the workspace once the commits
  are on GitHub.

Do not mark the Replit requirement passed until every mandatory track item in
`Rules.md` and the public deployment have been independently checked.
