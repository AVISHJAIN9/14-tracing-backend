"""
Collector High-Availability and Failover Management.
Provides active-standby and multi-replica routing for OTLP collector nodes,
ensuring zero loss of acknowledged span batches during node crashes or failover events.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from storage.models import SpanRecord

@dataclass
class CollectorNode:
    node_id: str
    is_alive: bool = True
    processed_count: int = 0

class CollectorFailoverRouter:
    def __init__(self, primary_id: str = "collector-01", standby_id: str = "collector-02"):
        self.nodes: Dict[str, CollectorNode] = {
            primary_id: CollectorNode(node_id=primary_id, is_alive=True),
            standby_id: CollectorNode(node_id=standby_id, is_alive=True)
        }
        self.primary_id = primary_id
        self.standby_id = standby_id
        self.active_id = primary_id
        self.failover_count = 0
        self.replicated_batches: List[List[Dict[str, Any]]] = []

    def mark_node_failure(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].is_alive = False
            if self.active_id == node_id:
                # Trigger automatic failover to the surviving standby node
                available = [n_id for n_id, n in self.nodes.items() if n.is_alive]
                if available:
                    self.active_id = available[0]
                    self.failover_count += 1
                else:
                    self.active_id = ""

    def mark_node_recovered(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].is_alive = True
            if not self.active_id:
                self.active_id = node_id

    def route_batch(self, batch: List[Dict[str, Any]]) -> str:
        """
        Routes incoming span batch to the currently active collector node.
        Raises RuntimeError if all replicas are down.
        """
        if not self.active_id or not self.nodes.get(self.active_id, CollectorNode("")).is_alive:
            raise RuntimeError("No healthy collector node available; all replicas down")

        node = self.nodes[self.active_id]
        node.processed_count += len(batch)
        self.replicated_batches.append(batch)
        return self.active_id
