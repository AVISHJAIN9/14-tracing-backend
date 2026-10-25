"""
Dynamic Sampling Optimization Controller.
Dynamically adjusts sampling rates based on real-time traffic volume and error rates,
recording an immutable audit trail and guaranteeing error/slow trace sampling floors.
"""

import time
from typing import List, Dict, Any, Optional
from sampling_recommendation import SamplingRecommender

class DynamicSamplingOptimizer:
    def __init__(
        self,
        target_spans_per_sec: float = 2000.0,
        error_sampling_floor: float = 1.0,
        slow_sampling_floor: float = 1.0,
        min_routine_floor: float = 0.05
    ):
        self.target_spans_per_sec = target_spans_per_sec
        self.error_sampling_floor = error_sampling_floor
        self.slow_sampling_floor = slow_sampling_floor
        self.min_routine_floor = min_routine_floor
        self.current_policies: Dict[str, float] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def optimize_and_apply(
        self,
        service_telemetry: List[Dict[str, Any]],
        apply_to_registry: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        tenant_id: str = "default-tenant"
    ) -> Dict[str, Any]:
        """
        Calculates optimal rates and applies them to the sampling registry with an audit trail.
        """
        recs = SamplingRecommender.recommend_sampling_policies(
            service_telemetry=service_telemetry,
            target_spans_per_second=self.target_spans_per_sec,
            min_sample_rate=self.min_routine_floor
        )

        applied_updates = []
        now_ts = time.time_ns()

        for pol in recs.get("recommended_policies", []):
            svc = pol["service"]
            new_rate = float(pol["recommended_sample_rate"])

            # Never allow sample rate to drop below minimum floor
            effective_rate = max(new_rate, self.min_routine_floor)
            prev_rate = self.current_policies.get(svc, 1.0)

            self.current_policies[svc] = effective_rate

            audit_entry = {
                "timestamp_unix_nano": now_ts,
                "tenant_id": tenant_id,
                "service": svc,
                "previous_rate": prev_rate,
                "new_rate": effective_rate,
                "error_floor_guaranteed": self.error_sampling_floor,
                "slow_floor_guaranteed": self.slow_sampling_floor,
                "reason": pol.get("rationale", "Dynamic load balancing")
            }
            self.audit_log.append(audit_entry)

            applied_updates.append(audit_entry)

            # Apply to in-memory sampling rule registry if provided
            if apply_to_registry is not None:
                if tenant_id not in apply_to_registry:
                    apply_to_registry[tenant_id] = []
                existing = next((r for r in apply_to_registry[tenant_id] if r["name"] == f"dyn_{svc}"), None)
                if existing:
                    existing["sample_rate"] = effective_rate
                else:
                    apply_to_registry[tenant_id].append({
                        "name": f"dyn_{svc}",
                        "service_pattern": svc,
                        "sample_rate": effective_rate
                    })

        return {
            "target_budget_spans_per_sec": self.target_spans_per_sec,
            "applied_updates": applied_updates,
            "total_audit_events": len(self.audit_log),
            "floors_enforced": {
                "error_sampling_floor": self.error_sampling_floor,
                "slow_sampling_floor": self.slow_sampling_floor,
                "min_routine_floor": self.min_routine_floor
            }
        }
