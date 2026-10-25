"""
Per-Route Sampling Configuration.
Matches HTTP request routes (exact and parameterized templates like /users/{id})
and applies route-specific sampling decisions.
"""

import re
from typing import Dict, Optional, Any, Tuple
from .head import SamplingDecision, SamplingResult

class PerRouteSampler:
    def __init__(self, route_rates: Optional[Dict[str, float]] = None, default_rate: float = 0.1):
        self.route_rates: Dict[str, float] = dict(route_rates or {})
        self.default_rate = default_rate

    def set_route_rate(self, route_pattern: str, rate: float) -> None:
        if not (0.0 <= rate <= 1.0):
            raise ValueError(f"Rate must be between 0.0 and 1.0, got {rate}")
        self.route_rates[route_pattern] = rate

    def _match_route(self, route: str) -> Tuple[Optional[str], float]:
        # 1. Exact match
        if route in self.route_rates:
            return route, self.route_rates[route]

        # 2. Parameterized pattern match (e.g. /users/{id}/profile)
        for pattern, rate in self.route_rates.items():
            if "{" in pattern and "}" in pattern:
                # Convert {var} to [^/]+
                regex_pattern = "^" + re.sub(r"\{[a-zA-Z0-9_]+\}", r"[^/]+", pattern) + "$"
                if re.match(regex_pattern, route):
                    return pattern, rate

        return None, self.default_rate

    def should_sample(
        self,
        trace_id: str,
        route: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SamplingResult:
        matched_template, rate = self._match_route(route)

        try:
            val = int(trace_id, 16) % 1_000_000
            sampled = val < int(rate * 1_000_000)
        except (ValueError, TypeError):
            sampled = False

        decision = SamplingDecision.RECORD_AND_SAMPLE if sampled else SamplingDecision.DROP
        trace_flags = 0x01 if sampled else 0x00

        attrs = {
            "sampler.type": "per_route",
            "http.route": route,
            "route.sample_rate": rate
        }
        if matched_template:
            attrs["route.matched_template"] = matched_template

        return SamplingResult(
            decision=decision,
            attributes=attrs,
            trace_flags=trace_flags
        )
