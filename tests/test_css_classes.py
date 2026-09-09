"""The status dots and the page furniture must not share class names."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"live", "active", "configured", "applied", "pending", "unreachable"}


def _bare_class_selectors(css: str) -> set[str]:
    """Every rule whose selector is exactly one class, e.g. `.live{...}`."""
    bare: set[str] = set()
    for group in re.findall(r"([^{}]+)\{", css):
        for selector in group.split(","):
            match = re.fullmatch(r"\.([A-Za-z_][\w-]*)", selector.strip())
            if match:
                bare.add(match.group(1))
    return bare


def test_no_status_name_is_also_a_bare_css_class() -> None:
    """A dot is rendered as class="dot <status>".

    A bare `.<status>` rule therefore paints every dot of that status with the
    other element's styling. That is exactly how the live-integrations panel,
    once called `.live`, turned every green dot into a fixed 360px box in the
    corner of every page.
    """
    css = (ROOT / "app" / "web" / "site.css").read_text("utf-8")
    collisions = _bare_class_selectors(css) & STATUSES
    assert not collisions, f"status names used as standalone CSS classes: {sorted(collisions)}"


def test_the_dot_rule_still_covers_every_status() -> None:
    css = (ROOT / "app" / "web" / "site.css").read_text("utf-8")
    for status in STATUSES:
        assert f".dot.{status}" in css, status


def test_the_live_panel_is_namespaced() -> None:
    css = (ROOT / "app" / "web" / "site.css").read_text("utf-8")
    script = (ROOT / "app" / "web" / "site.js").read_text("utf-8")
    assert ".livepanel{" in css and ".livepanel[hidden]" in css
    assert "'livepanel'" in script
