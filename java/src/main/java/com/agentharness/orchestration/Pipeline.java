package com.agentharness.orchestration;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.Decision;
import com.agentharness.model.DecisionAction;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Sequential Pipeline orchestration (harness-protocol.md §6.1).
 *
 * <p>Agents run in order. Each stage receives the prior stage's decision in its {@code context} under
 * the {@code "pipeline"} key, so a later stage can react to what came before. Every stage is invoked
 * through {@link Harness#invoke}, so each passes the confidence gate and tool registry individually
 * (O-1).
 *
 * <p>The pipeline short-circuits on the first {@code BLOCK} or {@code DEFER} (spec §6.1): once a stage
 * refuses or defers, later stages do not run — the safe action stands and no further side effects are
 * risked.
 */
public final class Pipeline {

    /** Actions that stop the pipeline (spec §6.1). */
    private static final Set<DecisionAction> SHORT_CIRCUIT =
            Set.of(DecisionAction.BLOCK, DecisionAction.DEFER);

    private final Harness harness;
    private final List<Agent> stages;

    public Pipeline(Harness harness, List<Agent> stages) {
        if (stages == null || stages.isEmpty()) {
            throw new IllegalArgumentException("a pipeline requires at least one stage");
        }
        this.harness = harness;
        this.stages = List.copyOf(stages);
    }

    public PipelineResult run(AgentInput request) {
        Map<String, AgentOutput> outputs = new LinkedHashMap<>();
        String shortCircuitedAt = null;
        AgentInput current = request;
        DecisionAction finalAction = null;

        for (Agent stage : stages) {
            AgentOutput output = harness.invoke(stage, current);
            outputs.put(stage.name(), output);
            finalAction = output.decision().action();
            if (SHORT_CIRCUIT.contains(finalAction)) {
                shortCircuitedAt = stage.name();
                break;
            }
            current = withPrior(request, stage.name(), output);
        }

        return new PipelineResult(finalAction, Map.copyOf(outputs), shortCircuitedAt);
    }

    /**
     * Return a new AgentInput carrying the prior stage's decision in {@code context.get("pipeline")}.
     * Scope and metadata are preserved verbatim (spec §2.1).
     */
    private static AgentInput withPrior(AgentInput base, String stageName, AgentOutput output) {
        Decision decision = output.decision();
        Map<String, Object> pipeline = new HashMap<>();
        pipeline.put("prior_stage", stageName);
        pipeline.put("prior_action", decision.action().name());
        pipeline.put("prior_confidence", decision.confidence());
        pipeline.put("prior_rationale", decision.rationale());

        Map<String, Object> context = new HashMap<>(base.context());
        context.put("pipeline", pipeline);
        return new AgentInput(base.tenantId(), base.userId(), context, base.metadata());
    }
}
