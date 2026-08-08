"""Agent Contract loading + validation (spec §10, ADR-0006).

Validates a contract against ``docs/spec/agent-contract.schema.json`` and then applies the semantic
binding rule (declared capabilities must be within the declared authority level, spec §3.3) that the
JSON Schema alone cannot express. Requires the ``contract`` extra (jsonschema).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core.errors import ContractValidationError
from .core.model import AuthorityLevel, DecisionAction, action_within_authority


def _default_schema_path() -> Path:
    """Locate agent-contract.schema.json by walking up from this file to the repo root."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "spec" / "agent-contract.schema.json"
        if candidate.is_file():
            return candidate
    raise ContractValidationError("could not locate docs/spec/agent-contract.schema.json")


def load_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(schema_path) if schema_path else _default_schema_path()
    return json.loads(path.read_text())


def validate_contract(contract: dict[str, Any], schema_path: str | Path | None = None) -> dict[str, Any]:
    """Validate a contract dict; return it unchanged on success, else raise ContractValidationError."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ContractValidationError(
            "jsonschema is required to validate contracts (install the 'contract' extra)"
        ) from exc

    schema = load_schema(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        raise ContractValidationError(f"{list(first.path)}: {first.message}")

    # Semantic binding rule (spec §3.3): every declared capability must be within authorityLevel.
    authority = AuthorityLevel[contract["authorityLevel"]]
    for cap in contract["capabilities"]:
        if not action_within_authority(DecisionAction[cap], authority):
            raise ContractValidationError(
                f"capability {cap} exceeds declared authority {authority.name} (spec §3.3)"
            )
    return contract


def load_contract(path: str | Path, schema_path: str | Path | None = None) -> dict[str, Any]:
    """Load a contract JSON file and validate it (spec §10)."""
    contract = json.loads(Path(path).read_text())
    return validate_contract(contract, schema_path)
