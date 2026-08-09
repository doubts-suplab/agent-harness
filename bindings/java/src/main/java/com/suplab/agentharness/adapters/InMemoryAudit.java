package com.suplab.agentharness.adapters;

import com.suplab.agentharness.ports.AuditPort;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.UnaryOperator;

/**
 * Append-only audit log (harness-protocol.md §7.3). No update/delete API is exposed; PII is redacted
 * on write. The redaction strategy is pluggable — pass any {@code UnaryOperator<String>} (e.g. a
 * customized {@link RedactionStrategy}); it defaults to the built-in patterns.
 */
public final class InMemoryAudit implements AuditPort {

    private final List<AuditEntry> entries = new CopyOnWriteArrayList<>();
    private final List<SecurityEvent> securityEvents = new CopyOnWriteArrayList<>();
    private final UnaryOperator<String> redact;

    public InMemoryAudit() {
        this(RedactionStrategy.DEFAULT);
    }

    public InMemoryAudit(UnaryOperator<String> redactor) {
        this.redact = redactor;
    }

    @Override
    public void record(AuditEntry entry) {
        entries.add(new AuditEntry(entry.agentName(), entry.tenantId(), entry.action(), entry.confidence(),
                entry.autoEnforced(), redact.apply(entry.rationale()), entry.outcome(),
                entry.correlationId(), entry.recordedAt()));
    }

    @Override
    public void recordSecurityEvent(SecurityEvent event) {
        securityEvents.add(new SecurityEvent(event.agentName(), event.tenantId(), event.kind(),
                redact.apply(event.detail()), event.correlationId(), event.recordedAt()));
    }

    public List<AuditEntry> entries() {
        return List.copyOf(entries);
    }

    public List<SecurityEvent> securityEvents() {
        return List.copyOf(securityEvents);
    }
}
