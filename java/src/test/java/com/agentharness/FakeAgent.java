package com.agentharness;

import com.agentharness.model.AgentInput;
import com.agentharness.model.AuthorityLevel;
import com.agentharness.model.Decision;
import com.agentharness.model.DecisionAction;

import java.util.Set;
import java.util.function.BiFunction;

/** A minimal Agent whose decision is produced by an injected function (test helper). */
record FakeAgent(String name, AuthorityLevel authorityLevel, Set<DecisionAction> capabilities,
                 BiFunction<AgentInput, ToolInvoker, Decision> decide) implements Agent {

    @Override
    public Decision decide(AgentInput input, ToolInvoker tools) {
        return decide.apply(input, tools);
    }

    static FakeAgent of(String name, AuthorityLevel authority, Set<DecisionAction> caps,
                        DecisionAction action, double confidence) {
        return new FakeAgent(name, authority, caps,
                (in, tools) -> Decision.propose(action, confidence, "because"));
    }
}
