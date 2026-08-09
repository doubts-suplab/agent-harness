package com.suplab.agentharness.orchestration;

/**
 * How a {@link Debate} reconciles competing decisions (harness-protocol.md §6.4).
 *
 * <ul>
 *   <li>{@code SAFEST} — the strictest action wins, per the Decision Hierarchy (§3.3). Conservative:
 *       a single {@code BLOCK} beats any number of {@code ALLOW}s. The safe default for governance.</li>
 *   <li>{@code MAJORITY} — the most-proposed action wins; a tie resolves to {@code DEFER}
 *       (tie → human review). May de-escalate below the strictest proposal.</li>
 * </ul>
 */
public enum ConsensusRule {
    SAFEST,
    MAJORITY
}
