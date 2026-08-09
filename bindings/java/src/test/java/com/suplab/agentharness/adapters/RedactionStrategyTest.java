package com.suplab.agentharness.adapters;

import com.suplab.agentharness.ports.AuditPort.AuditEntry;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Pluggable redaction tests (harness-protocol.md §7.3). */
class RedactionStrategyTest {

    @Test
    void defaultStrategyCoversCommonPii() {
        assertFalse(Redaction.redact("mail bob@example.com").contains("bob@example.com"));
        assertTrue(Redaction.redact("mail bob@example.com").contains("[REDACTED_EMAIL]"));
        assertTrue(Redaction.redact("card 4111 1111 1111 1111").contains("[REDACTED_CARD]"));
        assertTrue(Redaction.redact("ssn 123-45-6789").contains("[REDACTED_SSN]"));
    }

    @Test
    void withRuleExtendsWithoutMutatingTheBase() {
        RedactionStrategy custom = RedactionStrategy.DEFAULT.withRule("ACME-\\d+", "[REDACTED_CASEID]");
        assertEquals("case [REDACTED_CASEID] for [REDACTED_EMAIL]",
                custom.redact("case ACME-42 for bob@example.com"));
        // The base strategy is unchanged (immutable).
        assertTrue(Redaction.redact("case ACME-42").contains("ACME-42"));
    }

    @Test
    void emptyStrategyRedactsNothing() {
        RedactionStrategy passthrough = new RedactionStrategy(List.of());
        assertEquals("bob@example.com", passthrough.redact("bob@example.com"));
    }

    @Test
    void auditUsesPluggableRedactor() {
        InMemoryAudit audit = new InMemoryAudit(RedactionStrategy.DEFAULT.withRule("topsecret", "[X]"));
        audit.record(new AuditEntry("a", "t1", "ALERT", 0.9, false,
                "topsecret and bob@example.com", "human-review", null, Instant.now()));
        String rationale = audit.entries().get(0).rationale();
        assertTrue(rationale.contains("[X]"));
        assertTrue(rationale.contains("[REDACTED_EMAIL]"));
    }
}
