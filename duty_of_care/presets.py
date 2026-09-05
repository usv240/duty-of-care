"""The demo library: self-authored screenplay presets a visitor can read, run, and download.

Every preset is original fiction written for this project and released under
CC0. No published screenplay is used, which the contest rules require. Each
record says what the deterministic layer is expected to notice so a reader can
check the tool against the stated expectation rather than trust a demo.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PRESET_DIR = Path(__file__).resolve().parents[1] / "presets"
DOWNLOAD_FORMATS = ("fountain", "txt", "json")


@dataclass(frozen=True)
class Preset:
    id: str
    title: str
    logline: str
    region: str
    expectation: str
    expected_trigger_classes: tuple[str, ...]
    expect_flag: bool
    text: str
    provenance: str = "self-authored demonstration screenplay, CC0-1.0"

    def summary(self) -> dict[str, object]:
        data = asdict(self)
        data["expected_trigger_classes"] = list(self.expected_trigger_classes)
        data.pop("text")
        data["scene_count"] = sum(
            1 for line in self.text.splitlines() if line[:4] in {"INT.", "EXT.", "I/E."}
        )
        data["characters"] = len(self.text)
        data["downloads"] = {
            fmt: f"/v1/presets/{self.id}/download?format={fmt}" for fmt in DOWNLOAD_FORMATS
        }
        return data

    def full(self) -> dict[str, object]:
        data = self.summary()
        data["text"] = self.text
        return data


def _load() -> list[Preset]:
    index = json.loads((PRESET_DIR / "index.json").read_text("utf-8"))
    presets: list[Preset] = []
    for record in index:
        text = (PRESET_DIR / record["file"]).read_text("utf-8").strip() + "\n"
        presets.append(
            Preset(
                id=record["id"],
                title=record["title"],
                logline=record["logline"],
                region=record.get("region", "US"),
                expectation=record["expectation"],
                expected_trigger_classes=tuple(record.get("expected_trigger_classes", [])),
                expect_flag=bool(record["expect_flag"]),
                text=text,
            )
        )
    return presets


_PRESETS: list[Preset] | None = None


def all_presets() -> list[Preset]:
    global _PRESETS
    if _PRESETS is None:
        _PRESETS = _load()
    return list(_PRESETS)


def get_preset(preset_id: str) -> Preset | None:
    for preset in all_presets():
        if preset.id == preset_id:
            return preset
    return None


def download_payload(preset: Preset, fmt: str) -> tuple[str, str, str]:
    """Return (content, media_type, filename) for a preset download."""
    if fmt == "json":
        return (
            json.dumps(preset.full(), indent=2) + "\n",
            "application/json",
            f"{preset.id}.json",
        )
    if fmt == "txt":
        return preset.text, "text/plain; charset=utf-8", f"{preset.id}.txt"
    header = (
        f"Title: {preset.title}\n"
        f"Credit: self-authored demonstration screenplay\n"
        f"Source: Duty of Care preset library ({preset.provenance})\n"
        f"Notes: {preset.logline}\n\n"
    )
    return header + preset.text, "text/plain; charset=utf-8", f"{preset.id}.fountain"
