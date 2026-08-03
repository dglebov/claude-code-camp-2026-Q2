"""Pytest bootstrap.

Puts the iteration root on sys.path so `boukensha` imports without being installed — the same
trick `examples/example.py` uses, and what lets every NN_step directory ship its own `boukensha`
package while sharing one virtualenv.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """A synthetic .boukensha directory, wired up as BOUKENSHA_DIR."""
    path = tmp_path / ".boukensha"
    path.mkdir()
    monkeypatch.setenv("BOUKENSHA_DIR", str(path))
    return path
