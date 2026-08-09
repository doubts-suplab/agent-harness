"""CLI tests (spec §10) — `halo validate-contract`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("jsonschema")  # the CLI validates against the schema

from halo_agent_harness.cli import main

_EXAMPLES = Path(__file__).resolve().parents[3] / "docs" / "spec" / "examples"
_ALL_EXAMPLES = sorted(str(p) for p in _EXAMPLES.glob("*.contract.json"))


def test_all_worked_examples_validate(capsys):
    assert _ALL_EXAMPLES, "expected worked example contracts to exist"
    code = main(["validate-contract", *_ALL_EXAMPLES])
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("VALID") == len(_ALL_EXAMPLES)


def test_missing_file_returns_2(capsys):
    code = main(["validate-contract", "does-not-exist.json"])
    assert code == 2
    assert "file not found" in capsys.readouterr().err


def test_schema_invalid_contract_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.contract.json"
    bad.write_text(json.dumps({"authorityLevel": "BLOCK"}))  # missing required fields
    code = main(["validate-contract", str(bad)])
    assert code == 1
    assert "INVALID" in capsys.readouterr().err


def test_capability_exceeding_authority_returns_1(tmp_path, capsys):
    # Schema-valid shape but the binding rule (spec §3.3) fails: OBSERVE agent claims BLOCK.
    contract = json.loads((_EXAMPLES / "observe-monitor.contract.json").read_text())
    contract["capabilities"] = ["ALLOW", "BLOCK"]
    path = tmp_path / "escalating.contract.json"
    path.write_text(json.dumps(contract))
    code = main(["validate-contract", str(path)])
    assert code == 1
    assert "exceeds declared authority" in capsys.readouterr().err


def test_mixed_batch_returns_worst_exit_code(tmp_path, capsys):
    good = str(_EXAMPLES / "governance-agent.contract.json")
    code = main(["validate-contract", good, "nope.json"])
    assert code == 2  # worst of VALID(0) and missing(2)
