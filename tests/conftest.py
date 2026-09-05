"""Shared fixtures: each test starts with an empty rate-limit window."""

from __future__ import annotations

import pytest

from duty_of_care import main


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    main._LIMITER.reset()
    main._HEALTH.update(checked=0.0, value=None)
