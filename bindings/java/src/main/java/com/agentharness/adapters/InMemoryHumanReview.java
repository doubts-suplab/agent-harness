package com.agentharness.adapters;

import com.agentharness.ports.HumanReviewPort;

import java.time.Instant;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

/**
 * In-memory human-review queue with SLA tracking and an audited override endpoint
 * (harness-protocol.md §7.4). Beyond {@code enqueue} it assigns each item a stable id, distinguishes
 * pending vs resolved, exposes overdue (SLA-breached) items for a monitor to sweep, and records
 * human overrides.
 */
public final class InMemoryHumanReview implements HumanReviewPort {

    /** A queued review item with a stable id and resolution state. */
    public static final class QueuedReview {
        private final long id;
        private final ReviewItem item;
        private volatile boolean resolved;
        private volatile OverrideRecord override;

        QueuedReview(long id, ReviewItem item) {
            this.id = id;
            this.item = item;
        }

        public long id() {
            return id;
        }

        public ReviewItem item() {
            return item;
        }

        public boolean resolved() {
            return resolved;
        }

        public OverrideRecord override() {
            return override;
        }
    }

    private final List<QueuedReview> queue = new CopyOnWriteArrayList<>();
    private final AtomicLong nextId = new AtomicLong(0);

    @Override
    public void enqueue(ReviewItem item) {
        queue.add(new QueuedReview(nextId.getAndIncrement(), item));
    }

    /** Backwards-compatible view of the queued items. */
    public List<ReviewItem> items() {
        return queue.stream().map(q -> q.item).toList();
    }

    public List<QueuedReview> queued() {
        return List.copyOf(queue);
    }

    public List<QueuedReview> pending() {
        return queue.stream().filter(q -> !q.resolved).toList();
    }

    /** Pending items whose SLA deadline has passed (spec §7.4). */
    public List<QueuedReview> overdue(Instant now) {
        return pending().stream().filter(q -> q.item.isOverdue(now)).toList();
    }

    /**
     * Record a human override of a queued decision (spec §7.4 — overrides are audited). Returns the
     * {@link OverrideRecord} so the caller can write it to the AuditPort.
     */
    public OverrideRecord resolve(long reviewId, String reviewer, String outcome) {
        QueuedReview q = find(reviewId);
        if (q.resolved) {
            throw new IllegalStateException("review " + reviewId + " is already resolved");
        }
        OverrideRecord record = new OverrideRecord(reviewId, q.item.agentName(),
                q.item.request().tenantId(), reviewer, outcome, Instant.now());
        q.resolved = true;
        q.override = record;
        return record;
    }

    private QueuedReview find(long reviewId) {
        for (QueuedReview q : queue) {
            if (q.id == reviewId) {
                return q;
            }
        }
        throw new IllegalArgumentException("no review with id " + reviewId);
    }
}
