"""Structured, content-free log lines that Cloud Logging lifts into jsonPayload.

Nothing here ever includes screenplay text, prompts, or generated prose. What is
logged is enough to reconstruct that a review happened, what the deterministic
layer noticed, what retrieval returned, and that the decision stayed with code
and the writer.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def emit(event: str, **fields: Any) -> None:
    record = {"severity": "INFO", "event": event, "component": "duty_of_care", **fields}
    sys.stdout.write(json.dumps(record, default=str, sort_keys=True) + "\n")
    sys.stdout.flush()
