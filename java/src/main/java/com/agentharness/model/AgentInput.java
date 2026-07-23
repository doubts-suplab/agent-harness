package com.agentharness.model;

import java.util.Map;
import java.util.Objects;

/**
 * One invocation's input (harness-protocol.md §2.1). {@code tenantId}/{@code userId} are the
 * multi-tenancy boundary. Records are immutable; collections are defensively copied.
 */
public record AgentInput(String tenantId, String userId,
                         Map<String, Object> context, Map<String, Object> metadata) {

    public AgentInput {
        tenantId = tenantId == null ? "" : tenantId;
        userId = userId == null ? "" : userId;
        context = context == null ? Map.of() : Map.copyOf(context);
        metadata = metadata == null ? Map.of() : Map.copyOf(metadata);
    }

    public static AgentInput of(String tenantId, String userId, Map<String, Object> context) {
        return new AgentInput(tenantId, userId, context, Map.of());
    }

    /** True if tenant and user scope are both present and non-empty (spec §2.1). */
    public boolean isScoped() {
        return !tenantId.isEmpty() && !userId.isEmpty();
    }

    /** Correlation/trace id to propagate into every port call (spec §7.5), or null. */
    public String correlationId() {
        Object cid = metadata.getOrDefault("correlationId", metadata.get("correlation_id"));
        return cid == null ? null : Objects.toString(cid);
    }
}
