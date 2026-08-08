package com.agentharness.adapters;

import com.agentharness.ports.LlmPort;

import java.util.List;

/**
 * A deterministic stub {@link LlmPort} for tests and local runs (harness-protocol.md §7). Parity with the
 * Python {@code StubLlm}. Real deployments supply an Anthropic/Groq/Ollama adapter satisfying the same port.
 */
public final class StubLlm implements LlmPort {

    private final String reply;
    private final String providerName;
    private final String model;

    public StubLlm() {
        this("ok", "stub", "stub-1");
    }

    public StubLlm(String reply) {
        this(reply, "stub", "stub-1");
    }

    public StubLlm(String reply, String providerName, String model) {
        this.reply = reply;
        this.providerName = providerName;
        this.model = model;
    }

    @Override
    public String providerName() {
        return providerName;
    }

    @Override
    public String model() {
        return model;
    }

    @Override
    public CompletionResult complete(List<Message> messages, String system, List<ToolDefinition> tools) {
        int inputTokens = messages == null ? 0
                : messages.stream().mapToInt(m -> m.content().split("\\s+").length).sum();
        return new CompletionResult(reply, List.of(), inputTokens, reply.split("\\s+").length, model, providerName);
    }
}
