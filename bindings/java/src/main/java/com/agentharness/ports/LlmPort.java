package com.agentharness.ports;

import java.util.List;
import java.util.Map;

/**
 * Provider-agnostic LLM access (harness-protocol.md §7). Mirrors the Python {@code LlmPort} and the
 * apex/grid provider shape so existing adapters (Anthropic/Groq/Ollama) plug in. Synchronous, matching
 * grid's {@code LlmClient}. No agent calls an SDK directly.
 */
public interface LlmPort {

    String providerName();

    String model();

    CompletionResult complete(List<Message> messages, String system, List<ToolDefinition> tools);

    /** A single chat message. */
    record Message(String role, String content) {
    }

    /** Describes a callable tool that can be offered to an LLM (spec §5.2). */
    record ToolDefinition(String name, String description, Map<String, Object> parameters, String sideEffect) {
    }

    /** A tool invocation requested by the LLM. */
    record ToolCall(String name, Map<String, Object> arguments, String id) {
    }

    /** Unified response from any LLM provider. */
    record CompletionResult(String content, List<ToolCall> toolCalls,
                            int inputTokens, int outputTokens, String model, String provider) {
        public CompletionResult {
            toolCalls = toolCalls == null ? List.of() : List.copyOf(toolCalls);
        }

        public static CompletionResult text(String content) {
            return new CompletionResult(content, List.of(), 0, 0, "", "");
        }
    }
}
