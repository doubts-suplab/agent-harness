package com.agentharness.adapters;

import com.agentharness.ports.AuditPort;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Append-only audit log (harness-protocol.md §7.3). No update/delete API is exposed; PII is redacted
 * on write.
 */
public final class InMemoryAudit implements AuditPort {

    private final List<AuditEntry> entries = new CopyOnWriteArrayList<>();
    private final List<SecurityEvent> securityEvents = new CopyOnWriteArrayList<>();

    @Override
    public void record(AuditEntry entry) {
        entries.add(new AuditEntry(entry.agentName(), entry.tenantId(), entry.action(), entry.confidence(),
                entry.autoEnforced(), Redaction.redact(entry.rationale()), entry.outcome(),
                entry.correlationId(), entry.recordedAt()));
    }

    @Override
    public void recordSecurityEvent(SecurityEvent event) {
        securityEvents.add(new SecurityEvent(event.agentName(), event.tenantId(), event.kind(),
                Redaction.redact(event.detail()), event.correlationId(), event.recordedAt()));
    }

    public List<AuditEntry> entries() {
        return List.copyOf(entries);
    }

    public List<SecurityEvent> securityEvents() {
        return List.copyOf(securityEvents);
    }
}
