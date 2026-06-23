"""Shared pytest fixtures.

The whole package must be importable from ``src/`` without being installed
first.  We also reset the cached settings between tests so each case can
mutate the environment freely.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``src/`` importable for editable-less test runs.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets a clean GOP_* env and a fresh ``get_settings()`` cache."""
    # Point data/ at a per-test tmp dir so registry files don't leak.
    monkeypatch.setenv("GOP_DATA_DIR", str(tmp_path / "data"))
    # Disable browser cookie source by default; tests opt in by overriding.
    monkeypatch.setenv("GOP_COOKIE_SOURCE", "env")
    monkeypatch.setenv("GOP_PROBE_ON_START", "false")
    # Keep httpx quiet in tests.
    monkeypatch.setenv("GOP_LOG_LEVEL", "WARNING")
    # Reset module-level cache.
    from gemini_openai_proxy.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()
