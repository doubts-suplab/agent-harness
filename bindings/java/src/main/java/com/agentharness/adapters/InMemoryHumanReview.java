package com.agentharness.adapters;

import com.agentharness.ports.HumanReviewPort;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** In-memory human review queue (harness-protocol.md §7.4). */
public final class InMemoryHumanReview implements HumanReviewPort {

    private final List<ReviewItem> items = new CopyOnWriteArrayList<>();

    @Override
    public void enqueue(ReviewItem item) {
        items.add(item);
    }

    public List<ReviewItem> items() {
        return List.copyOf(items);
    }
}
