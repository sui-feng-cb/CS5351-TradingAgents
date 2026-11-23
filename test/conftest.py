"""Pytest configuration for the B-module test tree.

Puts ``src/`` on ``sys.path`` so tests can ``import event_merge`` without the
package being installed, and registers the ``offline`` / ``live`` markers
required by D8 (see ``docs/code-governance/verification-constraints.md``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "offline: tests that run without network or API keys (default CI)",
    )
    config.addinivalue_line(
        "markers",
        "live: tests that require API/network access; run explicitly",
    )
