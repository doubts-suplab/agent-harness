package com.agentharness.ports;

import com.agentharness.model.AgentInput;
import com.agentharness.model.Decision;

import java.time.Instant;

/** Queue for decisions that must reach a human, with an SLA per item (harness-protocol.md §7.4). */
public interface HumanReviewPort {

    void enqueue(ReviewItem item);

    record ReviewItem(String agentName, AgentInput request, Decision decision,
                      String reason, int slaSeconds, Instant enqueuedAt) {
    }
}
