package com.suplab.agentharness.interop;

import com.suplab.agentharness.Agent;
import com.suplab.agentharness.ToolInvoker;
import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;

import java.util.Set;

/**
 * Adapts a legacy grid-style agent onto the harness {@link Agent} protocol.
 *
 * <p>Grid's agents currently each compute {@code autoEnforced = decision == BLOCK && confidence >= 0.8}
 * themselves (duplicated in {@code GovernanceAgent}, {@code TemporalPredictionAgent}, and the
 * {@code AgentOutput} backstop, with a hardcoded 0.8). Wrapping such an agent here strips that
 * responsibility away: the legacy agent only produces an <em>action + confidence + rationale</em>, and the
 * harness's single {@link com.suplab.agentharness.ConfidenceGate} decides enforcement. This is the migration path
 * for aether-grid — one gate, independently testable, impossible for an agent to bypass.
 */
public final class LegacyAgentAdapter implements Agent {

    /** What a legacy agent produces — no {@code autoEnforced}; that is the harness's job now. */
    public record LegacyResult(DecisionAction action, double confidence, String rationale) {
    }

    /** A legacy grid-style agent: pure function of the input to an action + confidence + rationale. */
    @FunctionalInterface
    public interface LegacyAgent {
        LegacyResult execute(AgentInput input);
    }

    private final String name;
    private final AuthorityLevel authorityLevel;
    private final Set<DecisionAction> capabilities;
    private final LegacyAgent delegate;

    public LegacyAgentAdapter(String name, AuthorityLevel authorityLevel,
                              Set<DecisionAction> capabilities, LegacyAgent delegate) {
        this.name = name;
        this.authorityLevel = authorityLevel;
        this.capabilities = Set.copyOf(capabilities);
        this.delegate = delegate;
    }

    @Override
    public String name() {
        return name;
    }

    @Override
    public AuthorityLevel authorityLevel() {
        return authorityLevel;
    }

    @Override
    public Set<DecisionAction> capabilities() {
        return capabilities;
    }

    @Override
    public Decision decide(AgentInput input, ToolInvoker tools) {
        LegacyResult r = delegate.execute(input);
        // propose(...) leaves autoEnforced=false — the harness gate sets it. No 0.8 check here.
        return Decision.propose(r.action(), r.confidence(), r.rationale());
    }
}
