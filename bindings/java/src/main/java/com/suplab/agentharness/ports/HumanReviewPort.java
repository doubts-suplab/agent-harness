package com.suplab.agentharness.ports;

import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.Decision;

import java.time.Instant;

/** Queue for decisions that must reach a human, with an SLA per item (harness-protocol.md §7.4). */
public interface HumanReviewPort {

    void enqueue(ReviewItem item);

    record ReviewItem(String agentName, AgentInput request, Decision decision,
                      String reason, int slaSeconds, Instant enqueuedAt) {

        /** When this item breaches its SLA (spec §7.4). */
        public Instant deadline() {
            return enqueuedAt.plusSeconds(slaSeconds);
        }

        public boolean isOverdue(Instant now) {
            return now.isAfter(deadline());
        }
    }

    /** A human override of a queued decision — itself auditable (spec §7.4). */
    record OverrideRecord(long reviewId, String agentName, String tenantId, String reviewer,
                          String outcome, Instant resolvedAt) {
    }
}
