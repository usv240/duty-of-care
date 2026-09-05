"""Drive every page in a real browser at phone and desktop widths.

Usage:
    python -m scripts.visual_check            # starts the app on a free port, checks, writes docs/img
    python -m scripts.visual_check --no-shots # check only

Fails on any console error, any page error, any horizontal overflow, a missing
crisis footer, or a missing sponsor ribbon. Runs in CI on every commit, because
a script that throws at init detaches every listener while every assertion
about static content still passes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
PAGES = ("/", "/presets", "/developers", "/stack")
PORT = int(os.getenv("VISUAL_CHECK_PORT", "8791"))


def main() -> int:
    shots = "--no-shots" not in sys.argv
    env = {**os.environ, "DUTY_OF_CARE_API_KEY_SECRET": "visual-check-secret", "DUTY_OF_CARE_STATE_DIR": str(ROOT / ".visual-state")}
    env.pop("VERTEX_SEARCH_DATA_STORE", None)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "duty_of_care.main:app", "--port", str(PORT), "--log-level", "warning"], env=env, cwd=ROOT)
    try:
        for _ in range(90):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/presets", timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            print("server did not start", file=sys.stderr)
            return 1
        from playwright.sync_api import sync_playwright

        failures: list[str] = []
        if shots:
            IMG.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, tag in ((1280, "desktop"), (390, "phone")):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.on("console", lambda m: failures.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
                page.on("pageerror", lambda e: failures.append(f"pageerror: {e}"))
                for path in PAGES:
                    page.goto(f"http://127.0.0.1:{PORT}{path}", wait_until="domcontentloaded")
                    page.wait_for_timeout(1200)
                    if page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"):
                        failures.append(f"{tag} {path}: horizontal overflow")
                    if not page.evaluate("!!document.querySelector('footer.crisis')"):
                        failures.append(f"{tag} {path}: crisis footer missing")
                    if page.evaluate("document.querySelectorAll('[data-stack-key]').length") < 14:
                        failures.append(f"{tag} {path}: sponsor ribbon incomplete")
                    if shots:
                        page.screenshot(path=str(IMG / f"{tag}-{path.strip('/') or 'home'}.png"), full_page=(width == 1280), timeout=20000)
                if width == 1280:
                    page.goto(f"http://127.0.0.1:{PORT}/?preset=guidance-case", wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                    page.click("button.primary")
                    page.wait_for_selector(".tally", timeout=20000)
                    page.wait_for_timeout(500)
                    if page.evaluate("document.querySelectorAll('mark.trig').length") < 3:
                        failures.append("review: triggering phrases not underlined")
                    if shots:
                        page.screenshot(path=str(IMG / "desktop-review.png"), full_page=True, timeout=20000)
                    page.goto(f"http://127.0.0.1:{PORT}/developers", wait_until="domcontentloaded")
                    page.wait_for_timeout(800)
                    page.click("[data-mint]")
                    page.wait_for_selector("[data-key]:not([hidden])", timeout=8000)
                    page.click("[data-run]")
                    page.wait_for_selector("[data-run-actions]:not([hidden])", timeout=20000)
                    if shots:
                        page.screenshot(path=str(IMG / "desktop-developers-run.png"), full_page=True, timeout=20000)
                    page.goto(f"http://127.0.0.1:{PORT}/stack", wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                    page.click("[data-theme-button]")
                    page.wait_for_timeout(300)
                    if page.evaluate("document.documentElement.dataset.theme") != "dark":
                        failures.append("stack: dark toggle did not apply")
                    if shots:
                        page.screenshot(path=str(IMG / "desktop-stack-dark.png"), full_page=True, timeout=20000)
                page.close()
            browser.close()
        for failure in failures:
            print("FAIL", failure, file=sys.stderr)
        print("visual check:", "failed" if failures else "passed", f"({len(PAGES)} pages x 2 widths)")
        return 1 if failures else 0
    finally:
        server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
