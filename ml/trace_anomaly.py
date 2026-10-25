"""
Trace Anomaly Detection using Isolation Forest.
Trained on baseline trace features: duration, span count, depth, error count, and fan-out.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

class TraceAnomalyDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
        self.is_fitted = False

    def extract_features(self, trace: Dict[str, Any]) -> List[float]:
        duration_ms = float(trace.get("duration_nanos", 0)) / 1_000_000.0
        span_count = float(trace.get("span_count", 1))
        max_depth = float(trace.get("max_depth", 1))
        error_count = float(trace.get("error_count", 0))
        max_fan_out = float(trace.get("max_fan_out", 1))
        return [duration_ms, span_count, max_depth, error_count, max_fan_out]

    def fit(self, traces: List[Dict[str, Any]]) -> "TraceAnomalyDetector":
        if not traces:
            raise ValueError("Cannot train TraceAnomalyDetector on empty traces list")

        X = np.array([self.extract_features(t) for t in traces], dtype=float)
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.is_fitted:
            # Fallback if not explicitly fitted: fit on current input if sufficient
            if len(traces) >= 5:
                self.fit(traces)
            else:
                return [
                    {
                        "trace_id": t.get("trace_id", ""),
                        "is_anomaly": False,
                        "anomaly_score": 0.0,
                        "reasons": []
                    }
                    for t in traces
                ]

        X = np.array([self.extract_features(t) for t in traces], dtype=float)
        preds = self.model.predict(X)  # -1 for anomaly, 1 for normal
        scores = self.model.decision_function(X)  # Lower is more abnormal

        results = []
        for i, t in enumerate(traces):
            is_anomaly = bool(preds[i] == -1)
            score = float(scores[i])
            reasons = []

            feats = X[i]
            if feats[3] > 0:
                reasons.append(f"Contains {int(feats[3])} error spans")
            if feats[0] > 1000.0:
                reasons.append(f"Elevated duration: {feats[0]:.1f}ms")
            if feats[1] > 50:
                reasons.append(f"High span count: {int(feats[1])}")

            results.append({
                "trace_id": t.get("trace_id", ""),
                "is_anomaly": is_anomaly,
                "anomaly_score": round(score, 4),
                "reasons": reasons
            })

        return results
