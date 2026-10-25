"""
Root-Cause Candidate Ranking Engine.
Scores trace spans using critical-path self-time, error propagation, and baseline deviation.
"""

from typing import List, Dict, Any, Optional

class RootCauseRanker:
    @staticmethod
    def rank_root_causes(
        spans: List[Dict[str, Any]],
        critical_path_ids: Optional[Any] = None,
        service_baselines_ms: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        if not spans:
            return []

        cp_set = set(critical_path_ids or [])
        baselines = service_baselines_ms or {}

        # 1. Compute self-time per span (duration minus non-overlapping child time)
        by_id = {s["span_id"]: s for s in spans}
        children: Dict[str, List[Dict[str, Any]]] = {}
        for s in spans:
            pid = s.get("parent_span_id")
            if pid and pid in by_id:
                children.setdefault(pid, []).append(s)

        total_trace_duration = max((s.get("duration_nanos", 1) for s in spans), default=1)
        candidates = []

        for s in spans:
            sid = s["span_id"]
            svc = s.get("service_name", "unknown")
            dur_ns = s.get("duration_nanos", 0)
            dur_ms = dur_ns / 1_000_000.0

            # Child duration sum
            child_dur_sum = sum(c.get("duration_nanos", 0) for c in children.get(sid, []))
            self_time_ns = max(0, dur_ns - child_dur_sum)
            self_time_ratio = self_time_ns / max(total_trace_duration, 1)

            # Critical path weight
            is_on_cp = sid in cp_set or not cp_set
            cp_weight = 1.0 if is_on_cp else 0.25

            # Error weight
            has_error = (
                s.get("status_code") == "ERROR" or
                bool(s.get("events") and any("error" in str(e).lower() for e in s["events"])) or
                bool(s.get("attributes") and any("error" in str(k).lower() for k in s["attributes"]))
            )
            error_weight = 1.0 if has_error else 0.0

            # Baseline deviation
            base_ms = baselines.get(svc, 25.0)
            dev_ratio = dur_ms / max(base_ms, 1.0)
            dev_weight = min(dev_ratio, 5.0) / 5.0

            # Composite Root Cause Score (0.0 to 1.0)
            composite_score = (
                (0.40 * self_time_ratio * cp_weight) +
                (0.40 * error_weight) +
                (0.20 * dev_weight)
            )

            reasons = []
            if has_error:
                reasons.append("Span status recorded ERROR")
            if is_on_cp and self_time_ratio > 0.3:
                reasons.append(f"Accounts for {self_time_ratio * 100:.1f}% exclusive critical-path self-time")
            if dev_ratio > 2.0:
                reasons.append(f"Duration {dur_ms:.1f}ms exceeds baseline {base_ms:.1f}ms by {dev_ratio:.1f}x")

            candidates.append({
                "span_id": sid,
                "service_name": svc,
                "name": s.get("name", "op"),
                "root_cause_score": round(float(composite_score), 4),
                "self_time_ms": round(self_time_ns / 1_000_000.0, 2),
                "is_critical_path": is_on_cp,
                "has_error": has_error,
                "baseline_deviation_ratio": round(dev_ratio, 2),
                "reasons": reasons
            })

        # Sort descending by root cause score
        candidates.sort(key=lambda x: x["root_cause_score"], reverse=True)
        return candidates
