"""Contract schema validation (spec §10). Requires the 'contract'/'test' extra (jsonschema)."""

from __future__ import annotations

from pathlib import Path

import pytest

from halo_agent_harness.contract import load_contract, load_schema, validate_contract
from halo_agent_harness.core.errors import ContractValidationError

# Repo root: this file lives at <root>/bindings/python/tests/, so the canonical docs are three up.
REPO = Path(__file__).resolve().parents[3]
EXAMPLE = REPO / "docs" / "spec" / "examples" / "governance-agent.contract.json"


def test_schema_is_valid_draft7():
    import jsonschema

    jsonschema.Draft7Validator.check_schema(load_schema())


def test_example_contract_validates():
    contract = load_contract(EXAMPLE)
    assert contract["identity"]["agentName"] == "governance-agent"


def test_capability_exceeding_authority_is_rejected():
    bad = {
        "identity": {"agentName": "x", "agentClass": "X", "version": "1.0"},
        "purpose": "test",
        "authorityLevel": "OBSERVE",
        "capabilities": ["BLOCK"],          # BLOCK requires BLOCK authority — violates §3.3
        "confidenceGate": {"threshold": 0.8, "escalationPath": "q"},
        "toolAccess": [],
        "inputContract": {"tenantScoped": True},
        "outputContract": {"emitsDecision": True},
        "failureBehaviour": [{"failure": "x", "action": "DEFER", "confidence": 0.5}],
        "governance": {"signoff": [{"role": "Governance Officer"}]},
    }
    with pytest.raises(ContractValidationError):
        validate_contract(bad)


def test_wildcard_tool_in_contract_is_rejected_by_schema():
    bad = {
        "identity": {"agentName": "x", "agentClass": "X", "version": "1.0"},
        "purpose": "test",
        "authorityLevel": "BLOCK",
        "capabilities": ["BLOCK"],
        "confidenceGate": {"threshold": 0.95, "escalationPath": "q"},
        "toolAccess": [{"tool": "db*", "permission": "Read"}],   # wildcard → schema pattern fails
        "inputContract": {"tenantScoped": True},
        "outputContract": {"emitsDecision": True},
        "failureBehaviour": [{"failure": "x", "action": "DEFER", "confidence": 0.5}],
        "governance": {"signoff": [{"role": "Governance Officer"}]},
    }
    with pytest.raises(ContractValidationError):
        validate_contract(bad)
