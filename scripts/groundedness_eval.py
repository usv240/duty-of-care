"""Judge the agent's answers with the Vertex AI Gen AI Evaluation Service.

Usage:
    python -m scripts.groundedness_eval --base https://<backend>

Runs every preset through the live review, then asks the evaluation service two
questions about each guidance note: is the explanation grounded in the agent's
inputs (the clauses Agent Search retrieved, the scene under review, and the
deterministic triggers), and is the whole answer safe? Writes
docs/EVAL-GROUNDEDNESS.json with per-note scores and rationales. No scene text
is written; note ids, scores, and the judge's rationale are.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from duty_of_care import vertex_eval

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "EVAL-GROUNDEDNESS.json"
ALTERNATIVE_HEADING = "One alternative that keeps the drama"


def _mint(base: str) -> str:
    request = urllib.request.Request(f"{base.rstrip('/')}/v1/keys", data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return str(json.loads(response.read().decode("utf-8"))["data"]["api_key"])


def _review(base: str, key: str, preset_id: str, region: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base.rstrip('/')}/v1/review",
        data=json.dumps({"preset_id": preset_id, "region": region}).encode(),
        headers={"content-type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
            if exc.code == 429 and attempt < 5:
                time.sleep(min(int(exc.headers.get("Retry-After", "10") or 10), 70))
                continue
            raise
    raise RuntimeError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    presets = json.loads((ROOT / "presets" / "index.json").read_text("utf-8"))
    key = _mint(args.base)
    notes: list[dict[str, Any]] = []
    started = time.perf_counter()
    for preset in presets:
        body = _review(args.base, key, preset["id"], preset.get("region", "US"))
        scenes = {scene["scene_id"]: scene for scene in body["data"]["scenes"]}
        whole = "\n\n".join(f"{scene['heading']}\n{scene['text']}" for scene in body["data"]["scenes"])
        for flag in body["data"]["grounded_flags"]:
            agent = flag["agent"]
            text = str(agent.get("text", ""))
            # Groundedness is judged on the explanation. The alternative is a proposal by
            # design (new text the writer may take or leave); it is covered by the hard
            # filter, Model Armor, and the safety judgement below, not by groundedness.
            explanation = text.split(ALTERNATIVE_HEADING, 1)[0] if ALTERNATIVE_HEADING in text else text
            scene_text = whole if flag.get("document_level") else scenes.get(flag["scene_id"], {}).get("text", "")
            context = vertex_eval.clause_context(
                flag["clauses"], body["meta"].get("region"), scene_text=scene_text, triggers=flag["triggers"]
            )
            grounded = vertex_eval.groundedness(explanation, context)
            safe = vertex_eval.safety(text)
            record = {
                "preset": preset["id"],
                "scene_id": flag["scene_id"],
                "document_level": bool(flag.get("document_level")),
                "clauses": len(flag["clauses"]),
                "evidence": len(flag.get("evidence", [])),
                "runtime": agent.get("runtime"),
                "safety_filter": agent.get("safety_filter"),
                "model_armor": (agent.get("model_armor") or {}).get("status"),
                "groundedness": grounded,
                "safety": safe,
            }
            notes.append(record)
            sys.stderr.write(
                f"{preset['id']}/{flag['scene_id']}: groundedness {grounded['score']} safety {safe['score']}\n"
            )
    g_scores = [float(n["groundedness"]["score"]) for n in notes if n["groundedness"]["score"] is not None]
    s_scores = [float(n["safety"]["score"]) for n in notes if n["safety"]["score"] is not None]
    report = {
        "ran_at": datetime.now(UTC).isoformat(),
        "target": args.base,
        "judge": "Vertex AI Gen AI Evaluation Service (pointwise groundedness and safety, model-based)",
        "notes_evaluated": len(notes),
        "groundedness": {
            "mean": round(statistics.mean(g_scores), 3) if g_scores else None,
            "fully_grounded_notes": sum(1 for s in g_scores if s >= 1.0),
            "distribution": {str(k): sum(1 for s in g_scores if s == k) for k in sorted(set(g_scores))},
            "what_it_measures": (
                "whether every claim in the agent's explanation section is attributable to its "
                "inputs: the clauses Agent Search returned, the scene under review, and the "
                "deterministic triggers. The alternative is a proposal by design and is judged "
                "for safety, by the hard filter, and by Model Armor rather than for groundedness"
            ),
        },
        "safety": {
            "mean": round(statistics.mean(s_scores), 3) if s_scores else None,
            "safe_notes": sum(1 for s in s_scores if s >= 1.0),
        },
        "wall_clock_seconds": round(time.perf_counter() - started, 1),
        "not_measured": [
            "whether a human adviser would agree with the explanation",
            "whether the alternative reads well to a writer",
        ],
        "notes": notes,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({k: v for k, v in report.items() if k != "notes"}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
