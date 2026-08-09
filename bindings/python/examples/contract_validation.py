"""Load + validate Agent Contracts (spec §10).

Run:  python examples/contract_validation.py

Validates the worked example contracts against the JSON Schema *and* the semantic binding rule
(declared capabilities must be within the declared authority level, spec §3.3), then shows the binding
rule rejecting a contract that claims a capability beyond its authority. Requires the ``contract`` extra
(jsonschema).
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.contract import load_contract, validate_contract
from agent_harness.core.errors import ContractValidationError

# examples/ -> bindings/python -> bindings -> repo root
_EXAMPLES = Path(__file__).resolve().parents[3] / "docs" / "spec" / "examples"


def main() -> None:
    for path in sorted(_EXAMPLES.glob("*.contract.json")):
        contract = load_contract(path)
        print(f"VALID    {path.name:38} authority={contract['authorityLevel']:8} "
              f"capabilities={contract['capabilities']}")

    # Now show the binding rule catching a self-escalation: an OBSERVE agent claiming BLOCK.
    escalating = {
        "schemaVersion": "1.0",
        "identity": {"agentName": "sneaky", "agentClass": "X", "capabilityEnum": "X",
                     "ownerService": "demo", "version": "1.0.0"},
        "purpose": "Tries to claim a capability beyond its authority.",
        "authorityLevel": "OBSERVE",
        "capabilities": ["ALLOW", "BLOCK"],
        "confidenceGate": {"threshold": 0.8, "escalationPath": "q"},
        "toolAccess": [],
        "inputContract": {"tenantScoped": True, "requiredContextKeys": []},
        "outputContract": {"emitsDecision": True, "rationaleAlwaysPresent": True},
        "failureBehaviour": [],
        "testingRequirements": ["x"],
        "governance": {"signoff": [{"role": "Agent Engineer"}]},
    }
    try:
        validate_contract(escalating)
    except ContractValidationError as exc:
        print(f"\nREJECTED escalating contract, as expected:\n  {exc}")


if __name__ == "__main__":
    main()
