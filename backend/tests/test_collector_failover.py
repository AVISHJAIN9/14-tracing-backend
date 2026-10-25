import pytest
from collector.failover import CollectorFailoverRouter

def test_TRC_136_collector_failover():
    router = CollectorFailoverRouter(primary_id="collector-node-a", standby_id="collector-node-b")

    batch1 = [{"span_id": "s1"}, {"span_id": "s2"}]
    batch2 = [{"span_id": "s3"}]
    batch3 = [{"span_id": "s4"}, {"span_id": "s5"}]

    # Initially, primary node processes incoming traffic
    active = router.route_batch(batch1)
    assert active == "collector-node-a"
    assert router.nodes["collector-node-a"].processed_count == 2
    assert router.failover_count == 0

    # Simulate Primary Collector node crash / kill
    router.mark_node_failure("collector-node-a")
    assert not router.nodes["collector-node-a"].is_alive
    assert router.active_id == "collector-node-b"
    assert router.failover_count == 1

    # Ingestion continues seamlessly on standby node with zero data loss
    active = router.route_batch(batch2)
    assert active == "collector-node-b"
    assert router.nodes["collector-node-b"].processed_count == 1

    active = router.route_batch(batch3)
    assert active == "collector-node-b"
    assert router.nodes["collector-node-b"].processed_count == 3

    # Total replicated batches across failover
    total_spans_received = sum(len(b) for b in router.replicated_batches)
    assert total_spans_received == 5  # Zero lost spans
