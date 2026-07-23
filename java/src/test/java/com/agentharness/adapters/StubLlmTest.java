package com.agentharness.adapters;

import com.agentharness.ports.LlmPort;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** The stub LLM adapter satisfies LlmPort and round-trips (harness-protocol.md §7). */
class StubLlmTest {

    @Test
    void completesWithCannedReply() {
        LlmPort llm = new StubLlm("hello world");
        LlmPort.CompletionResult result =
                llm.complete(List.of(new LlmPort.Message("user", "hi there")), null, null);
        assertEquals("hello world", result.content());
        assertEquals(2, result.outputTokens());
        assertEquals("stub", result.provider());
    }
}
