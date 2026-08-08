package com.agentharness.adapters;

import com.agentharness.ports.AuditPort.AuditEntry;
import com.agentharness.ports.AuditPort.SecurityEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Durable append-only file AuditPort tests (harness-protocol.md §7.3). */
class FileAuditTest {

    private static final Instant NOW = Instant.parse("2026-08-08T12:00:00Z");

    private static AuditEntry entry(String rationale, String action) {
        return new AuditEntry("a", "t1", action, 0.9, false, rationale, "human-review", "corr-1", NOW);
    }

    private static SecurityEvent event(String detail) {
        return new SecurityEvent("a", "t1", "tool_not_authorized", detail, "corr-1", NOW);
    }

    @Test
    void writesOneJsonLinePerRecord(@TempDir Path dir) {
        FileAudit audit = new FileAudit(dir.resolve("audit.jsonl"));
        audit.record(entry("ok", "BLOCK"));
        audit.recordSecurityEvent(event("tool=db"));
        List<String> lines = audit.lines();
        assertEquals(2, lines.size());
        assertTrue(lines.get(0).contains("\"type\":\"decision\""));
        assertTrue(lines.get(0).contains("\"action\":\"BLOCK\""));
        assertTrue(lines.get(1).contains("\"type\":\"security_event\""));
    }

    @Test
    void isAppendOnlyAcrossInstances(@TempDir Path dir) {
        Path path = dir.resolve("audit.jsonl");
        new FileAudit(path).record(entry("first", "ALERT"));
        // A fresh adapter over the same file appends, never truncates.
        FileAudit second = new FileAudit(path);
        second.record(entry("second", "ALERT"));
        List<String> lines = second.lines();
        assertEquals(2, lines.size());
        assertTrue(lines.get(0).contains("first"));
        assertTrue(lines.get(1).contains("second"));
    }

    @Test
    void piiIsRedactedBeforeWrite(@TempDir Path dir) {
        FileAudit audit = new FileAudit(dir.resolve("audit.jsonl"));
        audit.record(entry("email bob@example.com now", "ALERT"));
        audit.recordSecurityEvent(event("card 4111 1111 1111 1111"));
        String raw = String.join("\n", audit.lines());
        assertFalse(raw.contains("bob@example.com"));
        assertTrue(raw.contains("[REDACTED_EMAIL]"));
        assertFalse(raw.contains("4111 1111 1111 1111"));
        assertTrue(raw.contains("[REDACTED_CARD]"));
    }

    @Test
    void emptyLogReadsAsEmpty(@TempDir Path dir) {
        assertTrue(new FileAudit(dir.resolve("audit.jsonl")).lines().isEmpty());
    }
}
