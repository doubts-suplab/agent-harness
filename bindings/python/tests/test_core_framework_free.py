"""INV-5 (spec §7): the core imports nothing third-party.

Scans the top-level imports of every module under core/, ports/, and orchestration/ and asserts each
resolves to the standard library or to agent_harness itself. Relative imports are always allowed.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "src" / "agent_harness"
FRAMEWORK_FREE_DIRS = ["core", "ports", "orchestration"]
STDLIB = set(sys.stdlib_module_names)
ALLOWED_FIRST_PARTY = {"agent_harness"}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import — internal, always fine
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_core_has_no_third_party_imports():
    offenders: dict[str, set[str]] = {}
    for d in FRAMEWORK_FREE_DIRS:
        for py in (PKG / d).rglob("*.py"):
            bad = {
                name
                for name in _top_level_imports(py)
                if name not in STDLIB and name not in ALLOWED_FIRST_PARTY
            }
            if bad:
                offenders[str(py.relative_to(PKG))] = bad
    assert not offenders, f"third-party imports in framework-free core: {offenders}"
