"""Smoke tests: every example script runs end-to-end without error."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_SCRIPTS = sorted(p.name for p in _EXAMPLES.glob("*.py"))


@pytest.mark.parametrize("script", _SCRIPTS)
def test_example_runs(script, capsys):
    if script == "contract_validation.py":
        pytest.importorskip("jsonschema")
    runpy.run_path(str(_EXAMPLES / script), run_name="__main__")
    assert capsys.readouterr().out  # the example printed something


def test_all_examples_are_covered():
    # Guard so a newly-added example gets a smoke test automatically.
    assert set(_SCRIPTS) >= {
        "quickstart.py",
        "orchestration.py",
        "contract_validation.py",
        "failure_modes.py",
    }
