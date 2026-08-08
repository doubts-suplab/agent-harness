package com.agentharness.adapters;

import com.agentharness.adapters.RuleBasedPolicy.PolicyRule;
import com.agentharness.ports.MemoryPort;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** MemoryPort + PolicyPort reference-adapter tests (harness-protocol.md §7). */
class MemoryPolicyTest {

    // -- Memory -----------------------------------------------------------
    @Test
    void inMemoryReadWriteAndTenantIsolation() {
        MemoryPort mem = new InMemoryMemory();
        assertTrue(mem.read("t1", "u1", "k").isEmpty());
        mem.write("t1", "u1", "secret", "tenant-1-only");
        assertEquals("tenant-1-only", mem.read("t1", "u1", "secret").orElseThrow());
        assertTrue(mem.read("t2", "u1", "secret").isEmpty()); // other tenant cannot read
        assertTrue(mem.read("t1", "u2", "secret").isEmpty()); // other user cannot read
    }

    @Test
    void memoryRequiresScope() {
        MemoryPort mem = new InMemoryMemory();
        assertThrows(IllegalArgumentException.class, () -> mem.write("", "u1", "k", 1));
        assertThrows(IllegalArgumentException.class, () -> mem.read("t1", "", "k"));
    }

    @Test
    void fileMemoryIsDurableAcrossInstances(@TempDir Path dir) {
        Path path = dir.resolve("mem.properties");
        new FileMemory(path).write("t1", "u1", "k", "42");
        assertEquals("42", new FileMemory(path).read("t1", "u1", "k").orElseThrow());
    }

    // -- Policy -----------------------------------------------------------
    @Test
    void defaultAllowAndDefaultDeny() {
        assertTrue(new RuleBasedPolicy(List.of(), true).permits("a", "BLOCK", "t1"));
        assertFalse(new RuleBasedPolicy(List.of(), false).permits("a", "BLOCK", "t1"));
    }

    @Test
    void firstMatchingRuleWins() {
        RuleBasedPolicy policy = new RuleBasedPolicy(List.of(
                new PolicyRule(false, null, "BLOCK", null),
                new PolicyRule(true, "trusted", "BLOCK", null)), true);
        assertFalse(policy.permits("trusted", "BLOCK", "t1")); // deny rule matches first
        assertTrue(policy.permits("trusted", "ALERT", "t1"));  // falls through to default
    }

    @Test
    void ruleScopingByAgentActionTenant() {
        RuleBasedPolicy policy = new RuleBasedPolicy(
                List.of(new PolicyRule(false, "bot", "ALERT", "acme")), true);
        assertFalse(policy.permits("bot", "ALERT", "acme"));
        assertTrue(policy.permits("bot", "ALERT", "other"));  // tenant doesn't match
        assertTrue(policy.permits("other", "ALERT", "acme")); // agent doesn't match
    }

    @Test
    void loadPolicyFromFile(@TempDir Path dir) throws Exception {
        Path path = dir.resolve("policy.txt");
        Files.writeString(path, "default deny\nallow gov ALERT *\n");
        RuleBasedPolicy policy = RuleBasedPolicy.load(path);
        assertTrue(policy.permits("gov", "ALERT", "t1"));
        assertFalse(policy.permits("gov", "BLOCK", "t1")); // default deny
    }
}
