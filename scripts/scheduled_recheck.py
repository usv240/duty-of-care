"""Nightly re-check for a Replit Scheduled Deployment.

Run command: ``python -m scripts.scheduled_recheck``

It hashes the approved guidance corpus, probes the Google backend's health, and
records only uptime metadata plus the corpus version in the decision store.
When the corpus version changes, the product tells signed-in writers that a
saved decision was made under older guidance. No screenplay text is read,
fetched, or stored.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from duty_of_care import replit_platform

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "guidance" / "corpus.json"


def backend_health(url: str) -> dict[str, object]:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - the record must say the probe failed
        return {"agent_runtime_ready": False, "product_surface": f"unreachable:{type(exc).__name__}"}


def main() -> int:
    url = os.getenv(
        "DUTY_OF_CARE_BACKEND_URL",
        "https://duty-of-care-agent-backend-109051079423.us-central1.run.app",
    )
    record = replit_platform.record_scheduled_recheck(
        corpus_path=CORPUS, backend_health=backend_health(url)
    )
    sys.stdout.write(json.dumps({"event": "scheduled_recheck", **record}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
