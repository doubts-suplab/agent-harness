"""MemoryPort + PolicyPort reference-adapter tests (spec §7)."""

from __future__ import annotations

import dataclasses

import pytest

from halo_agent_harness.adapters import (
    FileMemory,
    InMemoryMemory,
    PolicyRule,
    RuleBasedPolicy,
    load_policy,
)


# -- Memory ------------------------------------------------------------------
@pytest.fixture(params=["inmemory", "file"])
def memory(request, tmp_path):
    return InMemoryMemory() if request.param == "inmemory" else FileMemory(tmp_path / "mem.json")


def test_read_write_round_trip(memory):
    assert memory.read("t1", "u1", "k") is None
    memory.write("t1", "u1", "k", {"v": 1})
    assert memory.read("t1", "u1", "k") == {"v": 1}


def test_memory_is_tenant_isolated(memory):
    memory.write("t1", "u1", "secret", "tenant-1-only")
    assert memory.read("t2", "u1", "secret") is None  # different tenant cannot read it
    assert memory.read("t1", "u2", "secret") is None  # different user cannot read it


def test_memory_requires_scope(memory):
    with pytest.raises(ValueError):
        memory.write("", "u1", "k", 1)
    with pytest.raises(ValueError):
        memory.read("t1", "", "k")


def test_file_memory_is_durable_across_instances(tmp_path):
    path = tmp_path / "mem.json"
    FileMemory(path).write("t1", "u1", "k", 42)
    assert FileMemory(path).read("t1", "u1", "k") == 42  # a fresh instance sees the persisted value


# -- Policy ------------------------------------------------------------------
def test_default_allow_and_default_deny():
    assert RuleBasedPolicy(default_allow=True).permits("a", "BLOCK", "t1") is True
    assert RuleBasedPolicy(default_allow=False).permits("a", "BLOCK", "t1") is False


def test_first_matching_rule_wins():
    policy = RuleBasedPolicy(
        rules=(
            PolicyRule(effect="deny", action="BLOCK"),
            PolicyRule(effect="allow", agent="trusted", action="BLOCK"),
        ),
        default_allow=True,
    )
    # The deny rule matches first for everyone...
    assert policy.permits("trusted", "BLOCK", "t1") is False
    # ...but a non-BLOCK action falls through to the default.
    assert policy.permits("trusted", "ALERT", "t1") is True


def test_rule_scoping_by_agent_action_tenant():
    policy = RuleBasedPolicy(
        rules=(PolicyRule(effect="deny", agent="bot", action="ALERT", tenant="acme"),),
        default_allow=True,
    )
    assert policy.permits("bot", "ALERT", "acme") is False
    assert policy.permits("bot", "ALERT", "other") is True   # tenant doesn't match
    assert policy.permits("other", "ALERT", "acme") is True  # agent doesn't match


def test_policy_is_immutable_at_runtime():
    policy = RuleBasedPolicy(rules=(PolicyRule(effect="deny", action="BLOCK"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.default_allow = True  # cannot loosen the rules at runtime (INV-3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.rules[0].effect = "allow"


def test_invalid_rule_effect_rejected():
    with pytest.raises(ValueError):
        PolicyRule(effect="maybe")


def test_load_policy_from_file(tmp_path):
    import json

    path = tmp_path / "policy.json"
    path.write_text(json.dumps({
        "default_allow": False,
        "rules": [{"effect": "allow", "agent": "gov", "action": "ALERT"}],
    }))
    policy = load_policy(path)
    assert policy.permits("gov", "ALERT", "t1") is True
    assert policy.permits("gov", "BLOCK", "t1") is False  # default deny
