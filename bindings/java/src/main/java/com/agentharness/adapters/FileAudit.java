package com.agentharness.adapters;

import com.agentharness.ports.AuditPort;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.function.UnaryOperator;

/**
 * Durable, append-only file AuditPort (harness-protocol.md §7.3).
 *
 * <p>Writes one JSON object per line (JSONL) to a file in append mode. There is <b>no</b> update or
 * delete API — the log is append-only by construction (INV-4). PII is redacted before every write.
 * Dependency-free (a small hand-rolled JSON writer); a JDBC / object-store adapter follows the same
 * contract.
 */
public final class FileAudit implements AuditPort {

    private static final String DECISION = "decision";
    private static final String SECURITY = "security_event";

    private final Path path;
    private final UnaryOperator<String> redact;
    private final Object lock = new Object();

    public FileAudit(Path path) {
        this(path, Redaction::redact);
    }

    public FileAudit(Path path, UnaryOperator<String> redact) {
        this.path = path;
        this.redact = redact;
        try {
            if (path.getParent() != null) {
                Files.createDirectories(path.getParent());
            }
        } catch (IOException e) {
            throw new UncheckedIOException("cannot create audit directory", e);
        }
    }

    @Override
    public void record(AuditEntry e) {
        StringBuilder sb = new StringBuilder("{");
        field(sb, "type", DECISION).append(',');
        field(sb, "agent_name", e.agentName()).append(',');
        field(sb, "tenant_id", e.tenantId()).append(',');
        field(sb, "action", e.action()).append(',');
        raw(sb, "confidence", Double.toString(e.confidence())).append(',');
        raw(sb, "auto_enforced", Boolean.toString(e.autoEnforced())).append(',');
        field(sb, "rationale", redact.apply(e.rationale())).append(',');
        field(sb, "outcome", e.outcome()).append(',');
        nullableField(sb, "correlation_id", e.correlationId()).append(',');
        field(sb, "recorded_at", e.recordedAt().toString());
        sb.append('}');
        append(sb.toString());
    }

    @Override
    public void recordSecurityEvent(SecurityEvent e) {
        StringBuilder sb = new StringBuilder("{");
        field(sb, "type", SECURITY).append(',');
        field(sb, "agent_name", e.agentName()).append(',');
        field(sb, "tenant_id", e.tenantId()).append(',');
        field(sb, "kind", e.kind()).append(',');
        field(sb, "detail", redact.apply(e.detail())).append(',');
        nullableField(sb, "correlation_id", e.correlationId()).append(',');
        field(sb, "recorded_at", e.recordedAt().toString());
        sb.append('}');
        append(sb.toString());
    }

    /** Raw JSONL lines, for inspection. */
    public List<String> lines() {
        try {
            return Files.exists(path) ? Files.readAllLines(path, StandardCharsets.UTF_8) : List.of();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read audit log", e);
        }
    }

    public Path path() {
        return path;
    }

    // -- internals --------------------------------------------------------
    private void append(String line) {
        synchronized (lock) {
            try {
                Files.writeString(path, line + "\n", StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE, StandardOpenOption.APPEND);
            } catch (IOException e) {
                throw new UncheckedIOException("cannot append to audit log", e);
            }
        }
    }

    private static StringBuilder field(StringBuilder sb, String key, String value) {
        return sb.append('"').append(key).append("\":\"").append(escape(value)).append('"');
    }

    private static StringBuilder nullableField(StringBuilder sb, String key, String value) {
        if (value == null) {
            return sb.append('"').append(key).append("\":null");
        }
        return field(sb, key, value);
    }

    private static StringBuilder raw(StringBuilder sb, String key, String jsonValue) {
        return sb.append('"').append(key).append("\":").append(jsonValue);
    }

    private static String escape(String s) {
        StringBuilder out = new StringBuilder(s.length() + 8);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.toString();
    }
}
