"""HALO command-line interface.

Currently exposes ``halo validate-contract <path.json>`` — validating an Agent Contract against
``docs/spec/agent-contract.schema.json`` and the semantic binding rule (spec §3.3, §10). Installed as
the ``halo`` console script (see ``[project.scripts]``); also runnable as ``python -m halo_agent_harness``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .contract import load_contract
from .core.errors import ContractValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="halo", description="HALO agent-harness CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    vc = sub.add_parser(
        "validate-contract",
        help="Validate an Agent Contract JSON file against the schema + binding rule (spec §10)",
    )
    vc.add_argument("paths", nargs="+", metavar="CONTRACT", help="path(s) to contract JSON file(s)")
    vc.add_argument("--schema", default=None, help="override the schema path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate-contract":
        return _validate_contracts(args.paths, args.schema)
    return 2  # pragma: no cover — argparse enforces a known subcommand


def _validate_contracts(paths: Sequence[str], schema: str | None) -> int:
    exit_code = 0
    for path in paths:
        try:
            contract = load_contract(path, schema)
        except FileNotFoundError:
            print(f"ERROR    {path}: file not found", file=sys.stderr)
            exit_code = max(exit_code, 2)
        except ContractValidationError as exc:
            print(f"INVALID  {path}\n         {exc}", file=sys.stderr)
            exit_code = max(exit_code, 1)
        else:
            name = contract.get("identity", {}).get("agentName") or contract.get("name", "?")
            print(f"VALID    {path}  ({name}, authority={contract.get('authorityLevel', '?')})")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
