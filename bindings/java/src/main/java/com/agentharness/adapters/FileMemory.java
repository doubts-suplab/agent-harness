package com.agentharness.adapters;

import com.agentharness.ports.MemoryPort;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.Properties;

/**
 * Durable, tenant-scoped memory backed by a properties file, read fresh each call (harness-protocol.md
 * §7). Isolates by {@code (tenantId, userId, key)}. Values are persisted as strings (the in-memory
 * adapter keeps arbitrary objects); a JSON/JDBC adapter follows the same {@link MemoryPort} contract.
 */
public final class FileMemory implements MemoryPort {

    private final Path path;
    private final Object lock = new Object();

    public FileMemory(Path path) {
        this.path = path;
        try {
            if (path.getParent() != null) {
                Files.createDirectories(path.getParent());
            }
        } catch (IOException e) {
            throw new UncheckedIOException("cannot create memory directory", e);
        }
    }

    @Override
    public Optional<Object> read(String tenantId, String userId, String key) {
        String value = load().getProperty(InMemoryMemory.scope(tenantId, userId, key));
        return Optional.ofNullable(value);
    }

    @Override
    public void write(String tenantId, String userId, String key, Object value) {
        synchronized (lock) {
            Properties props = load();
            props.setProperty(InMemoryMemory.scope(tenantId, userId, key), String.valueOf(value));
            try (OutputStream out = Files.newOutputStream(path)) {
                props.store(out, "agent-harness memory (tenant-scoped)");
            } catch (IOException e) {
                throw new UncheckedIOException("cannot write memory", e);
            }
        }
    }

    public Path path() {
        return path;
    }

    private Properties load() {
        Properties props = new Properties();
        if (Files.exists(path)) {
            try (InputStream in = Files.newInputStream(path)) {
                props.load(in);
            } catch (IOException e) {
                throw new UncheckedIOException("cannot read memory", e);
            }
        }
        return props;
    }
}
