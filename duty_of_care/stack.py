"""What this service is built from, and which parts are answering right now.

A status dot is worth nothing if it is decorative, so each component reports one
of a few honest states instead of painting everything green:

    live          a round trip to a remote system completed within the last minute
    active        in use inside the process serving this request, provable from it
    configured    wired in code and ready, but not exercised by this process
    applied       used to build or verify the project, not part of the request path
    pending       required by the track and not yet done; only the owner can change it
    unreachable   configured but not answering right now

Every entry carries `how`, which is what a reader actually wants to know: not
that the project uses Agent Search, but what it asks Agent Search to do.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from importlib import metadata
from typing import Any


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except Exception:
        return None


def _entry(
    key: str,
    name: str,
    group: str,
    role: str,
    how: str,
    status: str,
    *,
    version: str | None = None,
    evidence: str | None = None,
    reference: str | None = None,
    link: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "group": group,
        "role": role,
        "how": how,
        "status": status,
        "version": version,
        "evidence": evidence,
        "reference": reference,
        "link": link,
    }


def build_stack(
    *,
    integrations: Mapping[str, Mapping[str, Any]],
    replit: Mapping[str, Any],
    api_keys_ready: bool,
    model: str,
    agent_engine: Mapping[str, Any] | None = None,
    model_armor: Mapping[str, Any] | None = None,
    evidence_store: bool = False,
    agent_quality: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    agent_engine = agent_engine or {}
    model_armor = model_armor or {}
    quality = agent_quality if agent_quality and agent_quality.get("notes_evaluated") else None
    vertex = bool(integrations.get("google_vertex", {}).get("ok"))
    search = bool(integrations.get("agent_search", {}).get("ok"))
    revision = os.getenv("K_REVISION")
    on_cloud_run = bool(revision)
    on_replit = bool(replit.get("runtime", {}).get("on_replit"))
    deployment = bool(replit.get("runtime", {}).get("deployment"))
    caps = replit.get("capabilities", {})
    agent_evidence = replit.get("agent_evidence", {})
    search_doc = integrations.get("agent_search", {}).get("document_id")

    components = [
        _entry(
            "gemini",
            f"Gemini on Vertex AI ({model})",
            "google",
            "Explains retrieved guidance. Decides nothing.",
            "Gemini runs inside a Google ADK agent bound to one scene. It can only see the "
            "clauses Agent Search returned and must run the deterministic safety filter as a "
            "tool before it answers. It cannot create a flag, change the scene, or score it.",
            "live" if vertex else "unreachable",
            version=_version("google-genai"),
            evidence="a live Vertex round trip completed within the last minute" if vertex else None,
            reference="duty_of_care/adk_app.py",
        ),
        _entry(
            "adk",
            "Google Agent Development Kit",
            "google",
            "The agent runtime.",
            "LlmAgent with explicit Gemini safety settings and two Python tools reading session "
            "state: get_bound_guidance, which hands the agent only the retrieved clauses for the "
            "scene under review, and check_alternative, which runs the same hard filter the API "
            "applies afterwards. Tool calls are read off the event stream and returned with the "
            "explanation. One definition runs in-process and on Agent Engine.",
            "active",
            version=_version("google-adk"),
            evidence="imported and serving in this process",
            reference="duty_of_care/adk_app.py",
        ),
        _entry(
            "agent_engine",
            "Vertex AI Agent Engine",
            "google",
            "The managed runtime for the same agent.",
            "The GuidanceContextReviewer is deployed to Agent Engine from duty_of_care_agent "
            "with the project's own filter shipped alongside it. The backend creates a session "
            "whose state carries the scene and the retrieved clauses, then streams the query. "
            "If the managed runtime fails, the identical agent runs in-process and the response "
            "says so.",
            (
                "live" if agent_engine.get("last_runtime") == "vertex_ai_agent_engine"
                else ("unreachable" if agent_engine.get("last_runtime") == "adk_in_process_fallback"
                      else ("configured" if agent_engine.get("resource") else "pending"))
            ),
            version=str(agent_engine.get("resource") or "").rsplit("/", 1)[-1] or None,
            evidence=(
                "the most recent review on this instance ran on Agent Engine"
                if agent_engine.get("last_runtime") == "vertex_ai_agent_engine"
                else ("configured; no review has run on this instance yet" if agent_engine.get("resource") else "AGENT_ENGINE_RESOURCE not set on this host")
            ),
            reference="infra/deploy_agent_engine.py",
        ),
        _entry(
            "model_armor",
            "Model Armor",
            "google",
            "Screens the agent's answer before the writer reads it.",
            "Google's managed screen for hate speech, harassment, sexually explicit and "
            "dangerous content, prompt-injection patterns, malicious URIs and sensitive data "
            "runs on the final text after the project's own filter. A match withholds the "
            "text; the clauses stay. Dangerous-content sits at high confidence only, because "
            "these scenes legitimately discuss suicide.",
            (
                "live" if model_armor.get("last_status") == "screened"
                else ("unreachable" if model_armor.get("last_status") == "error"
                      else ("configured" if model_armor.get("template") else "pending"))
            ),
            version=str(model_armor.get("template") or "").rsplit("/", 1)[-1] or None,
            evidence=(
                "the most recent review on this instance was screened"
                if model_armor.get("last_status") == "screened"
                else ("template configured; no review screened on this instance yet" if model_armor.get("template") else "MODEL_ARMOR_TEMPLATE not set on this host")
            ),
            reference="duty_of_care/model_armor.py",
        ),
        _entry(
            "agent_search",
            "Google Agent Search (Discovery Engine data store)",
            "google",
            "The only source of guidance text. No clause, no flag.",
            "Two structured Discovery Engine data stores. The guidance store holds 36 attributed "
            "clauses across five jurisdictions; each candidate scene is searched with its trigger "
            "classes and jurisdiction, then filtered in code so retrieval cannot smuggle an "
            "inapplicable clause into a note. The evidence store holds 14 research records "
            "verified against Europe PMC, retrieved per note so the writer sees why the guidance "
            "says what it says, including the studies that disagree.",
            "live" if search else "unreachable",
            evidence=f"live search returned document {search_doc}" if search_doc else None,
            reference="duty_of_care/grounding.py",
        ),
        _entry(
            "vertex_evaluation",
            "Vertex AI Gen AI Evaluation Service",
            "google",
            "An independent Google judge of the agent's answers.",
            "After the project's own filters and Model Armor have run, the evaluation service "
            "scores each note for groundedness (is every claim attributable to the clauses Agent "
            "Search returned?) and safety. The scores are published from /v1/eval/latest, so the "
            "number on the site is the number that ran.",
            "applied" if quality else "pending",
            evidence=(
                f"{quality['notes_evaluated']} notes judged on {str(quality.get('ran_at'))[:10]}: "
                f"mean groundedness {quality.get('groundedness', {}).get('mean')}, "
                f"mean safety {quality.get('safety', {}).get('mean')}"
                if quality else "run scripts/groundedness_eval.py against a deployment"
            ),
            reference="scripts/groundedness_eval.py",
        ),
        _entry(
            "cloud_monitoring",
            "Cloud Monitoring",
            "google",
            "Watches the public backend so a judge never finds it down first.",
            "An uptime check requests the presets endpoint from Google's probers every five "
            "minutes and asserts the response body names the guidance-case preset, which "
            "proves the app, not just the load balancer, answered.",
            "active",
            evidence="uptime check duty-of-care-health, 300 s period, content match",
            reference="docs/AUDIT-2026-09-04.md",
        ),
        _entry(
            "artifact_registry",
            "Artifact Registry",
            "google",
            "Holds the container images Cloud Build produces.",
            "Every Cloud Run deploy builds the image from source with Cloud Build and stores it "
            "in Artifact Registry; the serving revision is pinned to one immutable image.",
            "active" if on_cloud_run else "configured",
            evidence=f"revision {revision} runs an Artifact Registry image" if revision else None,
            reference="infra/deploy_cloud_run.ps1",
        ),
        _entry(
            "cloudrun",
            "Cloud Run",
            "google",
            "Runs the Google agent backend.",
            "A container on a dedicated duty-care-runtime service identity with startup CPU "
            "boost. The Replit product surface calls this backend over HTTPS for the "
            "allowlisted routes only.",
            "active" if on_cloud_run else "configured",
            version=revision,
            evidence=f"revision {revision} is serving this request" if revision else None,
            reference="infra/deploy_cloud_run.ps1",
        ),
        _entry(
            "secret_manager",
            "Secret Manager",
            "google",
            "Holds the API-key signing secret.",
            "The signing secret is mounted into Cloud Run as a secret reference, never "
            "committed and never printed. Keys are stateless HMAC tokens, so no key store "
            "exists to leak.",
            "active" if api_keys_ready and on_cloud_run else ("configured" if api_keys_ready else "pending"),
            evidence="signing secret is present in this process" if api_keys_ready else None,
            reference="SECURITY.md",
        ),
        _entry(
            "cloud_build",
            "Cloud Build",
            "google",
            "Runs the offline suite on Google infrastructure.",
            "Ruff and the pytest suite run in a python:3.12 step with Cloud Logging output; "
            "the Cloud Run deploy builds the container from source.",
            "applied",
            evidence="cloudbuild.ci.yaml; build id recorded in STATUS.md",
            reference="cloudbuild.ci.yaml",
        ),
        _entry(
            "cloud_logging",
            "Cloud Logging",
            "google",
            "Makes each review reconstructable without storing the screenplay.",
            "One structured line per review records the request id, caller tier, scene "
            "count, trigger classes, clause count, model, filter state, and latency. No "
            "screenplay text, no prompts, and no generated prose are logged.",
            "active",
            evidence="structured entries are written to stdout by this process",
            reference="duty_of_care/telemetry.py",
        ),
        _entry(
            "replit_agent",
            "Replit Agent",
            "partner",
            "Builds the product surface. Mandatory for the track.",
            "The owner runs the prompt in replit.md inside an authenticated Replit workspace. "
            "Agent inspects the repository, builds the writer-facing surface, adds tests, and "
            "explains its decisions; the transcript and commit are recorded as evidence. "
            "This status flips only when that evidence exists.",
            "active" if agent_evidence.get("present") else "pending",
            evidence=agent_evidence.get("summary"),
            reference="replit.md",
            link=agent_evidence.get("url"),
        ),
        _entry(
            "replit_deployment",
            "Replit Autoscale Deployment",
            "partner",
            "Hosts the public product on replit.app.",
            ".replit declares an autoscale deployment that runs this same FastAPI app. On "
            "Replit the app detects the deployment and reports its public domain here.",
            "active" if deployment else ("configured" if on_replit else "pending"),
            evidence=(
                f"serving from {replit.get('runtime', {}).get('domains')}"
                if deployment
                else ("workspace on Replit; not yet published" if on_replit else "no Replit deployment answered this request")
            ),
            reference=".replit",
        ),
        _entry(
            "replit_auth",
            "Replit Auth",
            "partner",
            "Optional sign-in so a writer can keep decisions.",
            "Anonymous review never requires sign-in. When Replit Auth identifies a writer, "
            "the app lets them save accept, dismiss, and expert-review decisions with their "
            "reasoning. Identity is read from the Replit-provided request headers only.",
            "active" if caps.get("auth", {}).get("ok") else "configured",
            evidence=caps.get("auth", {}).get("detail"),
            reference="duty_of_care/replit_platform.py",
        ),
        _entry(
            "replit_database",
            "Replit Database",
            "partner",
            "Stores decisions, never screenplays.",
            "Saved decisions hold the flag id, scene heading, decision, the writer's reason, "
            "clause ids, and the corpus version. The scene text is replaced by a hash so the "
            "nightly re-check can tell the writer when guidance changed without keeping "
            "their script.",
            "active" if caps.get("database", {}).get("ok") and caps.get("database", {}).get("backend") != "local_file" else "configured",
            evidence=caps.get("database", {}).get("detail"),
            reference="duty_of_care/replit_platform.py",
        ),
        _entry(
            "replit_app_storage",
            "Replit App Storage",
            "partner",
            "Holds a JSON export only when the writer asks for one.",
            "Pressing Export writes the review result to the app's bucket and returns a "
            "link. Nothing is stored unless the writer presses the button; on other hosts "
            "the same route falls back to a temporary local file and says so.",
            "active" if caps.get("object_storage", {}).get("ok") and caps.get("object_storage", {}).get("backend") != "local_file" else "configured",
            evidence=caps.get("object_storage", {}).get("detail"),
            reference="duty_of_care/replit_platform.py",
        ),
        _entry(
            "replit_scheduled",
            "Replit Scheduled Deployment",
            "partner",
            "Nightly re-check of the guidance corpus.",
            "scripts/scheduled_recheck.py runs on a schedule, hashes the approved corpus, "
            "probes the Google backend, and records only uptime metadata plus a notice for "
            "any saved decision made under an older corpus version.",
            "active" if caps.get("scheduled", {}).get("ok") else "configured",
            evidence=caps.get("scheduled", {}).get("detail"),
            reference="scripts/scheduled_recheck.py",
        ),
        _entry(
            "replit_secrets",
            "Replit Secrets",
            "partner",
            "Holds the backend URL and the key-signing secret on Replit.",
            "The Replit surface never receives a Google service-account key. It holds only "
            "DUTY_OF_CARE_BACKEND_URL and DUTY_OF_CARE_API_KEY_SECRET as Replit Secrets.",
            "active" if on_replit and api_keys_ready else "configured",
            reference="replit.md",
        ),
        _entry(
            "fastapi",
            "FastAPI",
            "app",
            "The API surface and the OpenAPI document at /docs.",
            "Pydantic validates every submission; the 250,000-character limit and the "
            "required disclaimer field live in the schema, not in the UI.",
            "active",
            version=_version("fastapi"),
            evidence="serving this request",
        ),
        _entry(
            "pytest",
            "pytest and Ruff",
            "app",
            "The offline suite.",
            "Trigger classes, filters, grounding applicability, API keys, presets, report "
            "rendering, and the Replit fallbacks each have tests that run without any "
            "credential.",
            "applied",
            version=_version("pytest"),
            reference="tests/",
        ),
    ]
    return {
        "components": components,
        "summary": {
            state: sum(1 for c in components if c["status"] == state)
            for state in ("live", "active", "configured", "applied", "pending", "unreachable")
        },
        "legend": {
            "live": "a round trip to a remote system completed within the last minute",
            "active": "in use in the process serving this request",
            "configured": "wired in code and ready, not exercised by this process",
            "applied": "used to build or verify this project, not part of the request path",
            "pending": "required by the track and not yet done; only the owner can change it",
            "unreachable": "configured but not answering right now",
        },
        "surface": "replit" if on_replit else ("cloud_run" if on_cloud_run else "local"),
    }
