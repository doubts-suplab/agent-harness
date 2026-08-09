package com.suplab.agentharness.ports;

import java.time.Instant;

/**
 * Append-only audit log (harness-protocol.md §7.3). Implementations MUST NOT update or delete, and
 * MUST redact PII before writing.
 */
public interface AuditPort {

    void record(AuditEntry entry);

    void recordSecurityEvent(SecurityEvent event);

    record AuditEntry(String agentName, String tenantId, String action, double confidence,
                      boolean autoEnforced, String rationale, String outcome,
                      String correlationId, Instant recordedAt) {
    }

    record SecurityEvent(String agentName, String tenantId, String kind, String detail,
                         String correlationId, Instant recordedAt) {
    }
}
