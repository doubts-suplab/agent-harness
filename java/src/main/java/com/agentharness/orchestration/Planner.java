package com.agentharness.orchestration;

import com.agentharness.model.AgentInput;

import java.util.List;

/**
 * Optional supervisor capability: choose which workers to delegate to (harness-protocol.md §6.3).
 *
 * <p>Planning is a pure coordination step — it selects names, it does not act — so it needs no tools.
 * A supervisor that also implements this interface engages a subset of workers; a plain supervisor
 * delegates to all of them.
 */
public interface Planner {

    /** Return the subset of {@code workerNames} to engage for this request. */
    List<String> plan(AgentInput request, List<String> workerNames);
}
