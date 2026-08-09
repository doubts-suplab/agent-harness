package com.suplab.agentharness;

/** Base class for all harness errors. */
public class HarnessException extends RuntimeException {
    public HarnessException(String message) {
        super(message);
    }
}
