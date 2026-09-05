"""Run the full pipeline over every shipped case and publish what it did.

Usage:
    python -m scripts.live_eval --base https://<backend>   # against a deployment
    python -m scripts.live_eval --local                     # in-process with ADC

The deterministic benchmark in /v1/eval/latest measures layer one alone. This
script measures what happens after it: whether Agent Search returned an
applicable clause for each candidate scene, whether every returned clause was
inside the allowed jurisdictions, whether the agent's answer had the required
structure and passed the hard filter, how often Model Armor withheld text, and
what it cost in time. Results go to docs/EVAL-LIVE.json, which the API serves
under /v1/eval/latest so the numbers on the site are the numbers that ran.

No case text is written to the report; only ids, counts, and states.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "EVAL-LIVE.json"
ALTERNATIVE_HEADING = "One alternative that keeps the drama"


def _cases() -> list[dict[str, Any]]:
    cases = []
    for item in json.loads((ROOT / "benchmark" / "scenes.json").read_text("utf-8")):
        cases.append({"id": item["id"], "screenplay": item["scene"], "region": "US", "expect_candidate": bool(item["expected_candidate"]), "source": "benchmark"})
    for item in json.loads((ROOT / "presets" / "index.json").read_text("utf-8")):
        text = (ROOT / "presets" / item["file"]).read_text("utf-8")
        classes = set(item["expected_trigger_classes"])
        cases.append({"id": item["id"], "screenplay": text, "region": item.get("region", "US"), "expect_candidate": bool(classes - {"signposting_absence"}), "expect_document_note": "signposting_absence" in classes, "source": "preset"})
    return cases


def _mint(base: str) -> str:
    request = urllib.request.Request(f"{base.rstrip('/')}/v1/keys", data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return str(json.loads(response.read().decode("utf-8"))["data"]["api_key"])


def _http(base: str, case: dict[str, Any], key: str | None) -> tuple[int, dict[str, Any], float]:
    started = time.perf_counter()
    headers = {"content-type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/v1/review",
        data=json.dumps({"screenplay": case["screenplay"], "region": case["region"]}).encode(),
        headers=headers,
        method="POST",
    )
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.status, json.loads(response.read().decode("utf-8")), time.perf_counter() - started
        except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
            body = exc.read().decode("utf-8") or "{}"
            if exc.code == 429 and attempt < 7:
                # The limiter is per minute per caller; honour Retry-After rather than count a
                # throttled request as a pipeline failure.
                time.sleep(min(int(exc.headers.get("Retry-After", "10") or 10), 70))
                continue
            return exc.code, json.loads(body), time.perf_counter() - started
    raise RuntimeError("unreachable")


async def _local(case: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    from fastapi.testclient import TestClient

    from duty_of_care.main import app

    started = time.perf_counter()
    response = await asyncio.to_thread(
        lambda: TestClient(app).post("/v1/review", json={"screenplay": case["screenplay"], "region": case["region"]})
    )
    return response.status_code, response.json(), time.perf_counter() - started


def _judge(case: dict[str, Any], status: int, body: dict[str, Any], seconds: float) -> dict[str, Any]:
    record: dict[str, Any] = {"id": case["id"], "source": case["source"], "region": case["region"], "status": status, "seconds": round(seconds, 2)}
    if status != 200:
        record["outcome"] = "error"
        record["error"] = (body.get("error") or {}).get("code")
        return record
    data, meta = body["data"], body["meta"]
    scene_candidates = {t["scene_id"] for t in data["trigger_candidates"] if t["scene_id"] != "document"}
    flagged_scenes = {f["scene_id"] for f in data["grounded_flags"] if not f.get("document_level")}
    allowed = {"GLOBAL", case["region"].upper()}
    clauses = [c for f in data["grounded_flags"] for c in f["clauses"]]
    record.update(
        {
            "candidate_scenes": len(scene_candidates),
            "grounded_scenes": len(flagged_scenes),
            "document_note": any(f.get("document_level") for f in data["grounded_flags"]),
            "clauses": len(clauses),
            "clauses_outside_jurisdiction": sum(1 for c in clauses if c["jurisdiction"] not in allowed),
            "clauses_without_matching_class": sum(
                1
                for f in data["grounded_flags"]
                for c in f["clauses"]
                if not set(c["trigger_classes"]) & {t["trigger_class"] for t in f["triggers"]}
            ),
            "agent_structured": sum(1 for f in data["grounded_flags"] if ALTERNATIVE_HEADING.lower() in str(f["agent"]["text"]).lower()),
            "agent_filter_rejected": sum(1 for f in data["grounded_flags"] if f["agent"]["safety_filter"] != "passed"),
            "agent_self_checks": sum(int(f["agent"].get("self_check_calls", 0)) for f in data["grounded_flags"]),
            "model_armor_withheld": sum(1 for f in data["grounded_flags"] if (f["agent"].get("model_armor") or {}).get("match")),
            "model_armor_screened": sum(1 for f in data["grounded_flags"] if (f["agent"].get("model_armor") or {}).get("status") == "screened"),
            "runtimes": sorted({str(f["agent"].get("runtime")) for f in data["grounded_flags"]}),
            "runtime_notes": sorted({str(f["agent"].get("runtime_note")) for f in data["grounded_flags"] if f["agent"].get("runtime_note")}),
            "withheld_notes": [
                {"scene_id": f["scene_id"], "structured": ALTERNATIVE_HEADING.lower() in str(f["agent"]["text"]).lower(), "filter": f["agent"]["safety_filter"]}
                for f in data["grounded_flags"] if f["agent"]["safety_filter"] != "passed"
            ],
            "gate_failed": meta["gate"]["failed"],
            "latency_ms": meta["latency_ms"],
        }
    )
    if case["expect_candidate"]:
        record["outcome"] = "grounded" if scene_candidates and flagged_scenes == scene_candidates else ("partially_grounded" if flagged_scenes else "not_grounded")
    elif case.get("expect_document_note"):
        record["outcome"] = "grounded" if record["document_note"] and not scene_candidates else "not_grounded"
    else:
        record["outcome"] = "clean" if not scene_candidates and not flagged_scenes else "false_candidate"
    return record


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="backend base URL")
    parser.add_argument("--local", action="store_true", help="run in-process with ADC")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--anonymous", action="store_true", help="do not mint a key (subject to anonymous limits)")
    args = parser.parse_args()
    if not args.base and not args.local:
        parser.error("give --base URL or --local")
    cases = _cases()
    key = None if (args.local or args.anonymous) else _mint(args.base)
    semaphore = asyncio.Semaphore(args.concurrency)

    async def run(case: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            if args.local:
                status, body, seconds = await _local(case)
            else:
                status, body, seconds = await asyncio.to_thread(_http, args.base, case, key)
            record = _judge(case, status, body, seconds)
            sys.stderr.write(f"{record['id']}: {record['outcome']} ({record['seconds']}s)\n")
            return record

    started = time.perf_counter()
    results = await asyncio.gather(*(run(case) for case in cases))
    ok = [r for r in results if r["status"] == 200]
    by_id = {c["id"]: c for c in cases}
    expected = [r for r in ok if by_id[r["id"]]["expect_candidate"]]
    document_only = [r for r in ok if not by_id[r["id"]]["expect_candidate"] and by_id[r["id"]].get("expect_document_note")]
    clean_expected = [r for r in ok if not by_id[r["id"]]["expect_candidate"] and not by_id[r["id"]].get("expect_document_note")]
    notes = sum(r.get("grounded_scenes", 0) + (1 if r.get("document_note") else 0) for r in ok)
    latencies = sorted(r["latency_ms"] for r in ok)
    report = {
        "ran_at": datetime.now(UTC).isoformat(),
        "target": args.base or "local",
        "caller": "keyed" if key else "anonymous",
        "cases": len(cases),
        "errors": len(results) - len(ok),
        "layer_two_and_three": {
            "candidate_scenes": sum(r.get("candidate_scenes", 0) for r in ok),
            "candidate_scenes_grounded": sum(r.get("grounded_scenes", 0) for r in ok),
            "retrieval_coverage": (sum(r.get("grounded_scenes", 0) for r in ok) / max(1, sum(r.get("candidate_scenes", 0) for r in ok))),
            "expected_cases_fully_grounded": sum(1 for r in expected if r["outcome"] == "grounded"),
            "expected_cases": len(expected),
            "control_cases_clean": sum(1 for r in clean_expected if r["outcome"] == "clean"),
            "control_cases": len(clean_expected),
            "document_only_cases_grounded": sum(1 for r in document_only if r["outcome"] == "grounded"),
            "document_only_cases": len(document_only),
            "clauses_retrieved": sum(r.get("clauses", 0) for r in ok),
            "clauses_outside_jurisdiction": sum(r.get("clauses_outside_jurisdiction", 0) for r in ok),
            "clauses_without_matching_class": sum(r.get("clauses_without_matching_class", 0) for r in ok),
            "notes": notes,
            "agent_answers_structured": sum(r.get("agent_structured", 0) for r in ok),
            "agent_filter_rejections": sum(r.get("agent_filter_rejected", 0) for r in ok),
            "agent_self_checks": sum(r.get("agent_self_checks", 0) for r in ok),
            "model_armor_screened": sum(r.get("model_armor_screened", 0) for r in ok),
            "model_armor_withheld": sum(r.get("model_armor_withheld", 0) for r in ok),
            "runtimes": sorted({rt for r in ok for rt in r.get("runtimes", [])}),
            "runtime_notes": sorted({note for r in ok for note in r.get("runtime_notes", [])}),
            "withheld_notes": [{"case": r["id"], **item} for r in ok for item in r.get("withheld_notes", [])],
        },
        "latency_ms": {
            "p50": latencies[len(latencies) // 2] if latencies else None,
            "p95": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None,
            "mean": round(statistics.mean(latencies)) if latencies else None,
            "wall_clock_seconds": round(time.perf_counter() - started, 1),
        },
        "not_measured": [
            "whether a retrieved clause is the best clause a human adviser would pick",
            "whether an explanation is proportionate to the scene",
            "whether a suggested alternative reads well to a writer",
        ],
        "results": results,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2) + "\n")
    return 0 if report["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
