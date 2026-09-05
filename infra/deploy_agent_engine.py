"""Deploy or update the GuidanceContextReviewer on Vertex AI Agent Engine.

Usage:
    python infra/deploy_agent_engine.py            # create or update
    python infra/deploy_agent_engine.py --delete   # remove

Prints the resource name to set as AGENT_ENGINE_RESOURCE on the Cloud Run
service. The agent code shipped is duty_of_care_agent plus duty_of_care.filters,
so the managed agent applies exactly the same hard filter as the backend.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import vertexai
from vertexai import agent_engines

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET = os.getenv("AGENT_ENGINE_STAGING_BUCKET", f"gs://{PROJECT}-duty-of-care-agent")
DISPLAY_NAME = "duty-of-care-guidance-reviewer"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The aiplatform "adk" extra pins google-adk below 2.0, which conflicts with the
# ADK 2.x this project runs; the agent_engines extra alone is enough for AdkApp.
REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines]==1.153.1",
    "google-adk==2.7.1",
    "google-genai==2.12.1",
    "pydantic==2.12.5",
    "cloudpickle==3.1.2",
]


def existing() -> agent_engines.AgentEngine | None:
    for engine in agent_engines.list(filter=f'display_name="{DISPLAY_NAME}"'):
        return engine
    return None


def main() -> int:
    os.chdir(ROOT)
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=BUCKET)
    current = existing()
    if "--delete" in sys.argv:
        if current is None:
            print("nothing to delete")
            return 0
        current.delete(force=True)
        print(f"deleted {current.resource_name}")
        return 0

    from duty_of_care_agent.app import app  # noqa: PLC0415 - after chdir so packaging sees the tree

    kwargs = dict(
        requirements=REQUIREMENTS,
        extra_packages=["duty_of_care_agent", "duty_of_care"],
        display_name=DISPLAY_NAME,
        description="Explains retrieved screen-guidance clauses for one scene; filter-checked alternative.",
        env_vars={"GEMINI_MODEL": MODEL, "GOOGLE_GENAI_USE_VERTEXAI": "true"},
    )
    if current is None:
        engine = agent_engines.create(agent_engine=app, **kwargs)
        print(f"created {engine.resource_name}")
    else:
        engine = current.update(agent_engine=app, **kwargs)
        print(f"updated {engine.resource_name}")
    print("set AGENT_ENGINE_RESOURCE=" + engine.resource_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
