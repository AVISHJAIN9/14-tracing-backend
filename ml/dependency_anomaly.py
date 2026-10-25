"""
Service Dependency Anomaly Detection.
Diffs dependency call volume, latency, and edge topologies against baseline window.
"""

from typing import List, Dict, Any

class DependencyAnomalyDetector:
    @staticmethod
    def detect_dependency_anomalies(
        baseline_edges: List[Dict[str, Any]],
        current_edges: List[Dict[str, Any]],
        latency_threshold_ratio: float = 1.75,
        volume_threshold_ratio: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detects topological changes (new/missing dependency edges) and
        call rate / latency regressions across microservice dependency edges.
        """
        base_map = {f"{e['caller']}->{e['callee']}": e for e in baseline_edges}
        curr_map = {f"{e['caller']}->{e['callee']}": e for e in current_edges}

        anomalies: List[Dict[str, Any]] = []

        # Check for new edges and metrics drift
        for key, curr in curr_map.items():
            caller = curr["caller"]
            callee = curr["callee"]
            curr_lat = float(curr.get("latency_ms", 0.0))
            curr_vol = float(curr.get("call_count", 0))

            if key not in base_map:
                anomalies.append({
                    "edge": key,
                    "caller": caller,
                    "callee": callee,
                    "anomaly_type": "NEW_DEPENDENCY_EDGE",
                    "severity": "WARNING",
                    "details": f"Unheralded communication edge observed: {caller} invoking {callee}"
                })
            else:
                base = base_map[key]
                base_lat = max(float(base.get("latency_ms", 1.0)), 0.1)
                base_vol = max(float(base.get("call_count", 1)), 1.0)

                lat_ratio = curr_lat / base_lat
                vol_ratio = curr_vol / base_vol

                if lat_ratio >= latency_threshold_ratio:
                    anomalies.append({
                        "edge": key,
                        "caller": caller,
                        "callee": callee,
                        "anomaly_type": "LATENCY_REGRESSION",
                        "severity": "CRITICAL",
                        "ratio": round(lat_ratio, 2),
                        "details": f"Dependency latency increased by {lat_ratio:.2f}x ({base_lat:.1f}ms -> {curr_lat:.1f}ms)"
                    })

                if vol_ratio >= volume_threshold_ratio or vol_ratio <= (1.0 / volume_threshold_ratio):
                    anomalies.append({
                        "edge": key,
                        "caller": caller,
                        "callee": callee,
                        "anomaly_type": "TRAFFIC_VOLUME_SURGE",
                        "severity": "WARNING",
                        "ratio": round(vol_ratio, 2),
                        "details": f"Call volume shifted by {vol_ratio:.2f}x ({int(base_vol)} -> {int(curr_vol)} calls)"
                    })

        # Check for missing expected edges
        for key, base in base_map.items():
            if key not in curr_map:
                anomalies.append({
                    "edge": key,
                    "caller": base["caller"],
                    "callee": base["callee"],
                    "anomaly_type": "MISSING_DEPENDENCY_EDGE",
                    "severity": "CRITICAL",
                    "details": f"Expected communication link disappeared: {base['caller']} did not contact {base['callee']}"
                })

        return anomalies
