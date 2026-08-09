package com.suplab.agentharness.adapters;

import com.suplab.agentharness.ports.KillSwitchPort;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Cross-process kill switch backed by a shared signal file (harness-protocol.md §7.6).
 *
 * <p>{@link #isEngaged()} checks the filesystem on every call, so a trip in one process (or by an
 * operator running {@code touch}) propagates to every process that shares the path — stopping the whole
 * deployment without a code deploy. A file is the least-dependency shared signal; a DB/Redis adapter
 * follows the same {@link KillSwitchPort} contract.
 */
public final class FileKillSwitch implements KillSwitchPort {

    private final Path path;

    public FileKillSwitch(Path path) {
        this.path = path;
    }

    @Override
    public boolean isEngaged() {
        return Files.exists(path);
    }

    /** Trip the switch — creates the signal file (idempotent). */
    public void engage() {
        try {
            if (path.getParent() != null) {
                Files.createDirectories(path.getParent());
            }
            if (!Files.exists(path)) {
                Files.createFile(path);
            }
        } catch (IOException e) {
            throw new UncheckedIOException("cannot engage kill switch", e);
        }
    }

    /** Clear the switch — removes the signal file (idempotent). */
    public void disengage() {
        try {
            Files.deleteIfExists(path);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot disengage kill switch", e);
        }
    }

    public Path path() {
        return path;
    }
}
