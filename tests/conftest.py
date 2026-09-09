"""Shared fixtures: each test starts with an empty rate-limit window."""

from __future__ import annotations

import pytest

from duty_of_care import main


@pytest.fixture(autouse=True)
def _fresh_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Unit tests must not inherit live workspace/deployment integrations.
    for name in (
        "DUTY_OF_CARE_API_KEY_SECRET",
        "DUTY_OF_CARE_BACKEND_URL",
        "REPL_ID",
        "VERTEX_SEARCH_DATA_STORE",
    ):
        monkeypatch.delenv(name, raising=False)
    main._LIMITER.reset()
    main._HEALTH.update(checked=0.0, value=None)
