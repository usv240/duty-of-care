# Duty of Care

[![CI](https://github.com/usv240/duty-of-care/actions/workflows/ci.yml/badge.svg)](https://github.com/usv240/duty-of-care/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Duty of Care is a guidance-grounded pre-review for independent screenwriters depicting suicide, self-harm, or addiction. It is not a censor, clinician, or certification system. Every note can be accepted, dismissed, or sent for expert review, and the writer remains the decision owner.

**Live Google runtime:** https://duty-of-care-agent-backend-109051079423.us-central1.run.app

Start with [`JUDGING.md`](JUDGING.md) and the machine-readable
[`submission-evidence.json`](submission-evidence.json). They explicitly preserve
the mandatory Replit blocker.

## Why this is more than a prompt

1. Auditable code identifies a narrow candidate and shows the exact rule and excerpt.
2. Google Agent Search retrieves applicable, versioned clauses from an approved corpus.
3. A request-bound Google ADK agent using Gemini explains only those retrieved clauses.
4. Hard filters reject certification language and suggestions that add method specificity.
5. The UI preserves citations and reasoning even when the writer dismisses a note.

No deterministic trigger plus applicable citation means no guidance flag. Gemini cannot create the flag, change the scene being reviewed, or make the final decision.

## Live acceptance evidence

The deployed `/health` endpoint currently reports successful round trips to Vertex AI, Agent Search, and Google ADK. The self-authored concerning case returns source-linked WHO and National Action Alliance clauses and a completed ADK explanation. The self-authored responsible depiction returns zero candidates and zero flags. Exact non-secret evidence is recorded in [`docs/LIVE-ACCEPTANCE.json`](docs/LIVE-ACCEPTANCE.json).

The Google runtime is complete. **Track eligibility is not yet complete:** a genuine Replit Agent build record and anonymous public Replit deployment still require an authenticated Replit session. Qualified independent review of the ten-fragment pack is also pending. See [`STATUS.md`](STATUS.md) and [`replit.md`](replit.md); neither is represented as done.

## Sources

The eight-record demonstration corpus records publisher, document title, jurisdiction, version, retrieval date, applicable trigger classes, and original URL. It is derived from public guidance from:

- [World Health Organization](https://www.who.int/publications/i/item/preventing-suicide-a-resource-for-filmmakers-and-others-working-on-stage-and-screen)
- [Samaritans](https://www.samaritans.org/about-samaritans/media-guidelines/guidance-portrayals-suicide-and-self-harm-drama/)
- [National Action Alliance for Suicide Prevention](https://theactionalliance.org/resource/national-recommendations-depicting-suicide)

The repository stores short attributed guidance records, not entire source publications. Multi-jurisdiction results stay separate rather than being silently reconciled.

## Run locally

Python 3.11 or newer is required.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m uvicorn duty_of_care.main:app --reload
```

Google-backed review additionally needs Application Default Credentials and:

```text
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
VERTEX_SEARCH_LOCATION=global
VERTEX_SEARCH_DATA_STORE=duty-of-care-guidance
GEMINI_MODEL=gemini-2.5-flash
```

Provision the structured Agent Search corpus with `infra/provision_agent_search.py` or `infra/provision_agent_search.ps1`. Deploy through `infra/deploy_cloud_run.ps1`.

## API

- `GET /health` performs cached live integration probes.
- `GET /v1/guidance` exposes the approved corpus and provenance.
- `GET /v1/resources` returns region-aware support resources.
- `GET /v1/samples` returns two self-authored demonstration scenes.
- `POST /v1/review` returns deterministic candidates, retrieved clauses, ADK explanations, human controls, and no overall score.

Example:

```bash
curl -X POST "$URL/v1/review" \
  -H "content-type: application/json" \
  -d '{"screenplay":"INT. KITCHEN - DAWN\nA friend stays and calls for support. END CARD: Call or text 988; help is available.","region":"US"}'
```

## Evaluation and safety

`benchmark/` contains 48 CC0 engineering cases. `evaluation/` contains the ten-fragment blinded review pack and reviewer form; its labels must come from a qualified independent reviewer, not the team. The tool never claims that the absence of a flag makes a scene safe.

Run the offline suite with:

```bash
python -m pytest -q
python -m ruff check .
```

See [`SECURITY.md`](SECURITY.md) for data handling and reporting. Crisis resources are always visible in the product. In the U.S., call or text 988; elsewhere, use [Find A Helpline](https://findahelpline.com/). In immediate danger, contact local emergency services.

## License

Apache-2.0. Demonstration screen fragments are self-authored and released under CC0 as recorded in their metadata.
