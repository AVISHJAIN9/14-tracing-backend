"""
Large Trace Processing and Verification.
Handles generation, topological traversal, and depth/fan-out metrics for traces with large span counts.
"""

from typing import List, Dict, Any
from storage.models import SpanRecord

class LargeTraceAnalyzer:
    @staticmethod
    def analyze_trace_topology(spans: List[SpanRecord]) -> Dict[str, Any]:
        """
        Analyzes the depth, fan-out, and integrity of a large trace without stack overflow.
        Uses iterative BFS / queue traversal to avoid recursion limits.
        """
        if not spans:
            return {
                "total_spans": 0,
                "max_depth": 0,
                "max_fan_out": 0,
                "root_spans": 0,
                "services": []
            }

        by_id = {s.span_id: s for s in spans}
        children: Dict[str, List[str]] = {}
        roots: List[str] = []

        for s in spans:
            pid = s.parent_span_id
            if not pid or pid not in by_id:
                roots.append(s.span_id)
            else:
                children.setdefault(pid, []).append(s.span_id)

        # Iterative BFS to compute depth
        max_depth = 0
        queue = [(root_id, 1) for root_id in roots]
        visited = set()

        while queue:
            curr_id, depth = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)
            if depth > max_depth:
                max_depth = depth

            for ch_id in children.get(curr_id, []):
                queue.append((ch_id, depth + 1))

        max_fan_out = max((len(c) for c in children.values()), default=0)
        unique_services = list({s.service_name for s in spans})

        return {
            "total_spans": len(spans),
            "max_depth": max_depth,
            "max_fan_out": max_fan_out,
            "root_spans": len(roots),
            "services": unique_services
        }
