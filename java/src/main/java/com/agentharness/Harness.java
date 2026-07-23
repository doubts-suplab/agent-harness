package com.agentharness;

import com.agentharness.adapters.InMemoryAudit;
import com.agentharness.adapters.InMemoryHumanReview;
import com.agentharness.adapters.InMemoryKillSwitch;
import com.agentharness.adapters.InMemoryObservability;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.Decision;
import com.agentharness.model.DecisionAction;
import com.agentharness.model.Decisions;
import com.agentharness.model.FailureMode;
import com.agentharness.ports.AuditPort;
import com.agentharness.ports.HumanReviewPort;
import com.agentharness.ports.KillSwitchPort;
import com.agentharness.ports.ObservabilityPort;

import java.time.Instant;
import java.util.Map;

/**
 * The Harness — safe, governed invocation of a single agent (harness-protocol.md §2–§8).
 *
 * <p>Every agent invocation flows through here: validate scope, honour the kill switch, run the agent
 * with a registry-enforced tool invoker, apply the confidence gate, route non-enforcing decisions to
 * human review, record audit + observability. On any failure it resolves to a safe, non-enforcing
 * decision (spec §8) — it never fails open.
 */
public final class Harness {

    public static final String BYPASS_COUNTER = "confidence_gate_bypass_total";

    private static final int SLA_BLOCK = 3600;
    private static final int SLA_DEFAULT = 14400;

    private final ToolRegistry registry;
    private final AuditPort audit;
    private final HumanReviewPort humanReview;
    private final ObservabilityPort observability;
    private final KillSwitchPort killSwitch;
    private final ConfidenceGate gate;

    public Harness(ToolRegistry registry, AuditPort audit, HumanReviewPort humanReview,
                   ObservabilityPort observability, KillSwitchPort killSwitch, ConfidenceGate gate) {
        this.registry = registry;
        this.audit = audit;
        this.humanReview = humanReview;
        this.observability = observability;
        this.killSwitch = killSwitch;
        this.gate = gate;
    }

    /** Convenience: a harness wired with in-memory reference adapters. */
    public static Harness withInMemoryAdapters() {
        return new Harness(new ToolRegistry(), new InMemoryAudit(), new InMemoryHumanReview(),
                new InMemoryObservability(), new InMemoryKillSwitch(), new ConfidenceGate());
    }

    public ToolRegistry registry() {
        return registry;
    }

    // -- public API ------------------------------------------------------
    public AgentOutput invoke(Agent agent, AgentInput request) {
        if (!request.isScoped()) {
            throw new UnscopedInvocationException("AgentInput MUST carry non-empty tenantId and userId");
        }
        long started = System.nanoTime();

        if (killSwitch.isEngaged()) {
            Decision decision = new Decision(DecisionAction.DEFER, 0.0,
                    "kill switch engaged — routed to human review", false);
            return finalise(agent, request, decision, started, "kill_switch");
        }

        Ran ran = runAgent(agent, request);
        return finalise(agent, request, ran.decision(), started, ran.reason());
    }

    // -- internals -------------------------------------------------------
    private record Ran(Decision decision, String reason) {
    }

    private Ran runAgent(Agent agent, AgentInput request) {
        ToolInvoker invoker = new BoundInvoker(agent.name(), request);
        Decision decision;
        try {
            decision = agent.decide(request, invoker);
        } catch (ToolNotAuthorizedException e) {
            return new Ran(FailureMode.TOOL_FAILURE.toDecision("unauthorized tool call"), "failure");
        } catch (RuntimeException e) {
            return new Ran(FailureMode.BAD_OUTPUT.toDecision(e.getClass().getSimpleName()), "failure");
        }

        // The agent must not set autoEnforced; the harness owns it (spec §2.2). Reset defensively.
        decision = decision.withAutoEnforced(false);

        if (!agent.capabilities().contains(decision.action())) {
            return new Ran(FailureMode.BAD_OUTPUT.toDecision("undeclared action " + decision.action()), "failure");
        }
        if (!Decisions.actionWithinAuthority(decision.action(), agent.authorityLevel())) {
            audit.recordSecurityEvent(new AuditPort.SecurityEvent(agent.name(), request.tenantId(),
                    "authority_violation",
                    "action=" + decision.action() + " authority=" + agent.authorityLevel(),
                    request.correlationId(), Instant.now()));
            return new Ran(FailureMode.OUT_OF_AUTHORITY.toDecision(decision.action().name()), "failure");
        }
        try {
            decision.validate();
        } catch (IllegalArgumentException e) {
            return new Ran(FailureMode.BAD_OUTPUT.toDecision(e.getMessage()), "failure");
        }
        return new Ran(decision, null);
    }

    private AgentOutput finalise(Agent agent, AgentInput request, Decision proposed, long started, String reason) {
        // The gate is the ONLY place autoEnforced is decided (spec §4, INV-1).
        Decision decision = gate.evaluate(proposed, agent.authorityLevel());

        // Defensive bypass detection — must never fire in a correct system (spec §4.2).
        if (gate.isBypass(decision, agent.authorityLevel())) {
            observability.incrementCounter(BYPASS_COUNTER);
            decision = decision.withAutoEnforced(false);
        }

        String outcome = decision.autoEnforced() ? "auto-enforced" : "human-review";

        if (!decision.autoEnforced()) {
            int sla = decision.action() == DecisionAction.BLOCK ? SLA_BLOCK : SLA_DEFAULT;
            humanReview.enqueue(new HumanReviewPort.ReviewItem(agent.name(), request, decision,
                    reason != null ? reason : reviewReason(decision), sla, Instant.now()));
        }

        audit.record(new AuditPort.AuditEntry(agent.name(), request.tenantId(), decision.action().name(),
                decision.confidence(), decision.autoEnforced(), decision.rationale(), outcome,
                request.correlationId(), Instant.now()));

        double durationMs = (System.nanoTime() - started) / 1_000_000.0;
        observability.emit(new ObservabilityPort.InvocationMetric(agent.name(), decision.action().name(),
                decision.confidence(), durationMs, outcome, request.correlationId()));

        return AgentOutput.now(decision, agent.name());
    }

    private static String reviewReason(Decision decision) {
        return switch (decision.action()) {
            case DEFER -> "defer";
            case SUGGEST -> "suggest";
            default -> "low_confidence";
        };
    }

    /** A ToolInvoker scoped to one agent + request; enforces the registry and records violations. */
    private final class BoundInvoker implements ToolInvoker {
        private final String agentName;
        private final AgentInput request;

        BoundInvoker(String agentName, AgentInput request) {
            this.agentName = agentName;
            this.request = request;
        }

        @Override
        public Object call(String toolName, Map<String, Object> arguments) {
            try {
                return registry.invoke(agentName, toolName, arguments);
            } catch (ToolNotAuthorizedException e) {
                audit.recordSecurityEvent(new AuditPort.SecurityEvent(agentName, request.tenantId(),
                        "tool_not_authorized", "tool=" + toolName, request.correlationId(), Instant.now()));
                throw e;
            }
        }
    }
}
