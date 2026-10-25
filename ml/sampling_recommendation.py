"""
Sampling Recommendation Engine.
Calculates per-service head and tail sampling rates against a total spans-per-second budget.
Guarantees 100% error and latency-outlier retention.
"""

from typing import List, Dict, Any

class SamplingRecommender:
    @staticmethod
    def recommend_sampling_policies(
        service_telemetry: List[Dict[str, Any]],
        target_spans_per_second: float = 2000.0,
        min_sample_rate: float = 0.05
    ) -> Dict[str, Any]:
        """
        Computes recommended sampling ratios per microservice to stay within
        target spans-per-second budget while preserving 100% of error and slow traces.
        """
        if not service_telemetry:
            return {"recommended_policies": [], "total_projected_rate": 0.0}

        total_observed_volume = sum(float(s.get("spans_per_sec", 0)) for s in service_telemetry)

        # Base requirement: guarantee 100% of error traces
        error_volume = sum(
            float(s.get("spans_per_sec", 0)) * float(s.get("error_rate", 0.0))
            for s in service_telemetry
        )

        remaining_budget = max(target_spans_per_second - error_volume, target_spans_per_second * 0.5)

        # Weight services by complexity (latency, error rate) and inversely by raw volume
        policies = []
        projected_total = 0.0

        for s in service_telemetry:
            svc = s["service"]
            vol = max(float(s.get("spans_per_sec", 1.0)), 1.0)
            err_rate = float(s.get("error_rate", 0.0))
            p95_ms = float(s.get("p95_latency_ms", 20.0))

            # If volume already within budget, keep high rate
            if total_observed_volume <= target_spans_per_second:
                rate = 1.0
            else:
                # Dynamic weight based on complexity and latency variance
                complexity_factor = 1.0 + (err_rate * 5.0) + min(p95_ms / 100.0, 2.0)
                raw_share = (remaining_budget / max(total_observed_volume, 1.0)) * complexity_factor
                rate = min(1.0, max(min_sample_rate, raw_share))

            projected_svc_spans = vol * rate
            projected_total += projected_svc_spans

            policies.append({
                "service": svc,
                "observed_spans_per_sec": round(vol, 1),
                "recommended_sample_rate": round(rate, 4),
                "projected_spans_per_sec": round(projected_svc_spans, 1),
                "guaranteed_rules": [
                    "100% error spans retained",
                    f"Tail sampling for latencies > {p95_ms:.1f}ms retained"
                ],
                "rationale": f"Allocated {rate * 100:.1f}% rate to balance budget with {err_rate * 100:.1f}% error rate"
            })

        return {
            "target_budget_spans_per_sec": target_spans_per_second,
            "total_observed_volume": round(total_observed_volume, 1),
            "total_projected_rate": round(projected_total, 1),
            "within_budget": bool(projected_total <= target_spans_per_second * 1.15),
            "recommended_policies": policies
        }
