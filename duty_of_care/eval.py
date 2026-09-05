"""The published number for the deterministic layer, computed from the shipped cases.

This measures layer one only: does code select the right candidate scenes and
leave conforming scenes alone. It says nothing about whether retrieved clauses
apply or whether explanations are proportionate; those questions belong to the
blinded expert review pack in evaluation/, which the team cannot label itself.
Serving the number from the same code that produced it keeps the landing page
from drifting away from reality.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .triggers import DOCUMENT_SCENE_ID, detect_triggers


def run_benchmark(root: Path) -> dict[str, Any]:
    path = root / "benchmark" / "scenes.json"
    cases = json.loads(path.read_text("utf-8"))
    tp = fp = fn = tn = 0
    per_class: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []
    for case in cases:
        triggers = [t for t in detect_triggers(case["scene"]) if t.scene_id != DOCUMENT_SCENE_ID]
        classes = {t.trigger_class for t in triggers}
        predicted = bool(triggers)
        expected = bool(case["expected_candidate"])
        if expected:
            wanted = case.get("expected_trigger")
            bucket = per_class.setdefault(wanted, {"expected": 0, "found": 0})
            bucket["expected"] += 1
            hit = predicted and (wanted in classes if wanted else True)
            if hit:
                tp += 1
                bucket["found"] += 1
            else:
                fn += 1
                failures.append({"id": case["id"], "expected": wanted, "found": sorted(classes)})
        elif predicted:
            fp += 1
            failures.append({"id": case["id"], "expected": None, "found": sorted(classes)})
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    live_path = root / "docs" / "EVAL-LIVE.json"
    live: dict[str, Any] | None = None
    if live_path.exists():
        published = json.loads(live_path.read_text("utf-8"))
        live = {key: value for key, value in published.items() if key != "results"}
        live["outcomes"] = {
            outcome: sum(1 for item in published.get("results", []) if item.get("outcome") == outcome)
            for outcome in ("grounded", "partially_grounded", "not_grounded", "clean", "false_candidate", "error")
        }
    return {
        "layer": "deterministic_triggers",
        "cases": len(cases),
        "provenance": "self-authored CC0 engineering cases in benchmark/scenes.json",
        "benchmark_sha256": sha256(path.read_bytes()).hexdigest(),
        "counts": {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn},
        "precision": precision,
        "recall": recall,
        "false_flag_rate": fp / (fp + tn) if fp + tn else None,
        "per_class": per_class,
        "failures": failures,
        "not_measured": [
            "whether a retrieved clause applies (citation precision)",
            "whether the ADK explanation is proportionate",
            "whether any suggested alternative reads well to a writer",
        ],
        "live_pipeline": live or {"status": "not_published", "how": "python -m scripts.live_eval --base <url>"},
        "independent_review": {
            "status": "pending",
            "pack": "evaluation/expert-review-set.json",
            "note": "Ten blinded fragments await a qualified independent reviewer; the team does not label them.",
        },
    }
