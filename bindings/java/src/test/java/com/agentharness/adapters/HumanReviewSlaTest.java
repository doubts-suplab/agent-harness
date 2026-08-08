package com.agentharness.adapters;

import com.agentharness.adapters.InMemoryHumanReview.QueuedReview;
import com.agentharness.model.AgentInput;
import com.agentharness.model.Decision;
import com.agentharness.model.DecisionAction;
import com.agentharness.ports.HumanReviewPort.OverrideRecord;
import com.agentharness.ports.HumanReviewPort.ReviewItem;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Human-review SLA enforcement + monitoring tests (harness-protocol.md §7.4). */
class HumanReviewSlaTest {

    private static final Instant T0 = Instant.parse("2026-08-08T12:00:00Z");

    private static ReviewItem item(int slaSeconds, Instant enqueuedAt, String agent, String tenant) {
        return new ReviewItem(agent, new AgentInput(tenant, "u1", Map.of(), Map.of()),
                Decision.propose(DecisionAction.DEFER, 0.5, "review me"), "defer", slaSeconds, enqueuedAt);
    }

    private static ReviewItem item(int slaSeconds) {
        return item(slaSeconds, T0, "a", "t1");
    }

    @Test
    void reviewItemDeadlineAndOverdue() {
        ReviewItem it = item(3600);
        assertEquals(T0.plusSeconds(3600), it.deadline());
        assertFalse(it.isOverdue(T0.plusSeconds(3599)));
        assertTrue(it.isOverdue(T0.plusSeconds(7200)));
    }

    @Test
    void enqueueAssignsIdsAndPending() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        q.enqueue(item(3600));
        q.enqueue(item(3600));
        assertEquals(List.of(0L, 1L), q.queued().stream().map(QueuedReview::id).toList());
        assertEquals(2, q.pending().size());
        assertEquals(2, q.items().size()); // backwards-compatible view
    }

    @Test
    void resolveMarksResolvedAndReturnsAuditedOverride() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        q.enqueue(item(3600, T0, "gov", "acme"));
        OverrideRecord record = q.resolve(0L, "alice", "approved");
        assertEquals(0L, record.reviewId());
        assertEquals("alice", record.reviewer());
        assertEquals("approved", record.outcome());
        assertEquals("gov", record.agentName());
        assertEquals("acme", record.tenantId());
        assertTrue(q.pending().isEmpty());
    }

    @Test
    void resolveUnknownOrDoubleThrows() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        q.enqueue(item(3600));
        assertThrows(IllegalArgumentException.class, () -> q.resolve(999L, "bob", "approved"));
        q.resolve(0L, "bob", "approved");
        assertThrows(IllegalStateException.class, () -> q.resolve(0L, "bob", "approved"));
    }

    @Test
    void overdueSweepFindsOnlyBreachedPendingItems() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        q.enqueue(item(3600));   // id 0 — breaches at T0+1h
        q.enqueue(item(14400));  // id 1 — breaches at T0+4h
        List<QueuedReview> overdue = q.overdue(T0.plusSeconds(7200));
        assertEquals(List.of(0L), overdue.stream().map(QueuedReview::id).toList());
    }

    @Test
    void slaMonitorEmitsBreachCounterOncePerItem() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        InMemoryObservability obs = new InMemoryObservability();
        q.enqueue(item(3600));
        q.enqueue(item(3600));
        SlaMonitor monitor = new SlaMonitor(q, obs);

        Instant now = T0.plusSeconds(7200);
        assertEquals(2, monitor.sweep(now).size());
        assertEquals(2, obs.counter(SlaMonitor.HUMAN_REVIEW_SLA_BREACH));

        monitor.sweep(now); // idempotent — no double count
        assertEquals(2, obs.counter(SlaMonitor.HUMAN_REVIEW_SLA_BREACH));
        assertEquals(2, monitor.breachCount());
    }

    @Test
    void resolvedItemsAreNotOverdue() {
        InMemoryHumanReview q = new InMemoryHumanReview();
        q.enqueue(item(3600));
        q.resolve(0L, "alice", "approved");
        assertTrue(q.overdue(T0.plusSeconds(18000)).isEmpty());
    }
}
