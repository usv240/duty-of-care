# Duty of Care public API

The review this site performs is the same review any tool can call. No account
is needed: every endpoint works anonymously at standard limits, and a key minted
in one click raises them. This document is the integrator's guide; the
OpenAPI document at `/docs` is the schema.

Base URL (Google agent backend): `https://duty-of-care-agent-backend-109051079423.us-central1.run.app`
The Replit product surface serves the same routes once deployed.

## Sixty-second start

```bash
BASE=https://duty-of-care-agent-backend-109051079423.us-central1.run.app
KEY=$(curl -s -X POST "$BASE/v1/keys" | python -c "import sys,json;print(json.load(sys.stdin)['data']['api_key'])")
curl -s -X POST "$BASE/v1/review" \
  -H "Authorization: Bearer $KEY" \
  -H "content-type: application/json" \
  -d '{"preset_id":"guidance-case","region":"US"}' | python -m json.tool | head -60
```

A Markdown report instead of JSON:

```bash
curl -s -X POST "$BASE/v1/review?format=markdown" -H "content-type: application/json" \
  -d '{"preset_id":"documentary-edit"}' -o review.md
```

## Access model

| Tier | How | Limits per minute |
|---|---|---|
| Anonymous | Send no credential | review 6 · keys 10 · exports 10 · decisions 30 |
| Keyed | `POST /v1/keys`, then `Authorization: Bearer <key>` or `X-API-Key: <key>` | 5x the anonymous limits |

Keys are stateless: `doc_<id>_<issued>_<signature>`, an HMAC over the id and
issue time using a secret held in Google Secret Manager. Nothing is stored when
a key is minted, so nothing can leak, and verification survives instance
restarts on Cloud Run and Replit Autoscale alike. The trade is that a single key
cannot be revoked without rotating the secret; keys expire after 90 days. A
present-but-broken key is a `401 invalid_api_key`; no key is never an error.

## Endpoints

| Route | Purpose |
|---|---|
| `POST /v1/review` | Review a screenplay. Body: `screenplay` (≤ 250,000 chars) or `preset_id`; optional `region` (`US`, `GB`, `CA`, `AU`). `?format=markdown` returns a report attachment. |
| `POST /v1/review/stream` | The same review as newline-delimited JSON progress events (`parsed`, `retrieving`, `retrieved`, `explaining`, `explained`, `complete`), ending with `result` (data and meta) or `error` (the error envelope). Same limits as review. |
| `POST /v1/report` | Render Markdown from a review payload you already hold. No model call. |
| `GET /v1/presets` · `GET /v1/presets/{id}` · `GET /v1/presets/{id}/download?format=fountain\|txt\|json` | The six self-authored demo drafts. |
| `GET /v1/samples` | The two original samples, kept for older clients. |
| `GET /v1/guidance` | The approved corpus with provenance and `corpus_version`. |
| `GET /v1/evidence` | The research behind the guidance: 14 records verified against Europe PMC, each with DOI, PMID, finding, writer-facing relevance, and trigger classes. The same records appear per note as `grounded_flags[].evidence` (up to three, retrieved from a second Agent Search store). |
| `GET /v1/resources?region=` | Region-aware support resources. |
| `GET /v1/eval/latest` | Deterministic-layer benchmark computed live from the 48 shipped cases with failures listed, the published live-pipeline evaluation from `docs/EVAL-LIVE.json`, and the Vertex AI Gen AI Evaluation Service groundedness and safety scores from `docs/EVAL-GROUNDEDNESS.json`. |
| `POST /v1/keys` · `GET /v1/keys/self` | Mint a key; inspect the identity and limits of the key you send. |
| `GET /v1/stack` · `GET /health` · `GET /health/integrations` | Which Google Cloud and Replit services are answering now, with evidence. |
| `POST /v1/exports` · `GET /v1/exports/{id}` | Store a review only when asked. Replit App Storage on Replit; a temporary file elsewhere. |
| `GET /v1/me` · `GET/POST/DELETE /v1/decisions` | Saved writer decisions for a signed-in Replit Auth user. Never stores screenplay text. |

## Response envelope

```json
{
  "ok": true,
  "data": {
    "scenes": [{"scene_id": "scene-001", "heading": "INT. ROOM - NIGHT", "text": "…"}],
    "trigger_candidates": [{"scene_id": "scene-001", "trigger_class": "method_specificity",
                            "matched_text": "exact amount", "match_start": 41, "match_end": 53,
                            "rule": "…", "evidence_excerpt": "…"}],
    "grounded_flags": [{"flag_id": "flag_…", "scene_id": "scene-001", "heading": "…",
                        "document_level": false,
                        "triggers": [...], "clauses": [{"clause_id": "naa-method-detail-2019",
                        "jurisdiction": "US", "publisher": "…", "document_title": "…",
                        "clause": "…", "source_url": "https://…", "version": "2019"}],
                        "jurisdictions": {"US": ["naa-method-detail-2019"], "GLOBAL": ["who-accuracy-2019"]},
                        "divergence": [{"trigger_class": "method_specificity", "jurisdictions": ["GLOBAL", "US"]}],
                        "evidence": [{"record_id": "niederkrotenthaler-2020-bmj-meta", "title": "…", "journal": "BMJ", "year": 2020,
                                      "doi": "10.1136/bmj.m575", "pmid": "32188637", "finding": "…", "relevance": "…"}],
                        "agent": {"model": "gemini-2.5-flash", "safety_filter": "passed",
                                  "runtime": "vertex_ai_agent_engine",
                                  "safety_settings": {"dangerous_content": "BLOCK_ONLY_HIGH", "...": "..."},
                                  "model_armor": {"status": "screened", "match": false, "matched_filters": []},
                                  "self_check_calls": 1, "tool_calls": [...], "text": "…",
                                  "decision_source": "deterministic_trigger_plus_agent_search_clause",
                                  "requires_human": true},
                        "state": "open"}],
    "grounding_status": "available",
    "writer_controls": ["accept", "dismiss", "request_expert_review"],
    "resources": [{"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988", "url": "…"}],
    "disclaimer": "No additional guidance conflicts were detected by this pre-review. This is not clinical or professional certification.",
    "decision_owner": "writer",
    "overall_score": null
  },
  "meta": {
    "request_id": "req_…", "latency_ms": 18420,
    "caller": {"tier": "keyed", "key_id": "…"},
    "verdict": "notes | candidates | no_candidates",
    "gate": {"passed": ["deterministic_candidate_present", "applicable_clause_retrieved",
                        "agent_explanation_completed", "safety_filter_passed", "grounding_available"],
             "failed": ["resource_signpost_present"]},
    "counts": {"scenes": 3, "candidates": 8, "notes": 3},
    "model_versions": {"gemini": "gemini-2.5-flash", "google_adk": "2.7.1"},
    "agent_runtime": ["vertex_ai_agent_engine"],
    "model_armor": "duty-of-care-agent-output",
    "region": "US", "region_known": true,
    "corpus_version": "…", "surface": "cloud_run",
    "abstained_because": null
  }
}
```

`data.disclaimer` and `data.overall_score: null` are required fields. `meta.gate`
lists every threshold that was evaluated, so a caller can see why a note exists
without reading prose. Thresholds: `deterministic_candidate_present`,
`applicable_clause_retrieved`, `agent_explanation_completed`, `safety_filter_passed`,
`model_armor_clear` (only when a template is configured), `resource_signpost_present`,
`grounding_available`. Regions: `US`, `GB`, `CA`, `AU`; any other value falls back to
global clauses and US resources and sets `meta.region_known` to false. A run with candidates but no applicable clause returns
`200` with `verdict: "candidates"`; that is a correct answer, not an error.

## Errors

```json
{"ok": false,
 "error": {"code": "rate_limited",
           "message": "review allows 6 requests per minute for this caller.",
           "fix": "Wait and retry, or POST /v1/keys for a key with 5x this limit.",
           "docs": "/docs"},
 "meta": {"request_id": "req_…"}}
```

Stable codes: `validation_error` (422), `invalid_api_key` (401),
`sign_in_required` (401), `preset_not_found` / `export_not_found` /
`decision_not_found` (404), `unsupported_format` (400), `disclaimer_required`
(422), `rate_limited` (429, with `Retry-After`), `api_keys_unavailable` /
`grounding_not_configured` (503), `grounding_failed` / `agent_review_failed`
(502). The 502s are fail-closed: no note is ever fabricated from model memory.

## What is logged and kept

Per review, one structured Cloud Logging line: request id, caller tier and key
id, region, scene count, trigger classes, note and clause counts, model, latency,
surface. Never logged: screenplay text, prompts, generated prose. Nothing is
stored by default. Exports and saved decisions are explicit actions; decisions
keep a hash of the scene, never its text.
