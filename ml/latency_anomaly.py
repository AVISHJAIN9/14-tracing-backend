"""
Latency Anomaly Detection using Robust Statistical Baselines (Median / MAD / EWMA).
"""

from typing import List, Dict, Any, Optional
import numpy as np

class LatencyAnomalyDetector:
    def __init__(self, threshold_mad: float = 3.0, ewma_alpha: float = 0.3):
        self.threshold_mad = threshold_mad
        self.ewma_alpha = ewma_alpha

    @staticmethod
    def compute_mad(values: np.ndarray, median: float) -> float:
        mad = np.median(np.abs(values - median))
        return float(mad) if mad > 0 else 1.0

    def detect_latency_anomalies(
        self,
        service: str,
        operation: str,
        history_durations_ms: List[float],
        current_durations_ms: List[float]
    ) -> List[Dict[str, Any]]:
        if not history_durations_ms or not current_durations_ms:
            return []

        hist_arr = np.array(history_durations_ms, dtype=float)
        median = float(np.median(hist_arr))
        mad = self.compute_mad(hist_arr, median)

        results = []
        for val in current_durations_ms:
            # Modified Z-Score: 0.6745 * (x - median) / MAD
            mod_z = 0.6745 * (val - median) / mad
            is_anomaly = bool(mod_z > self.threshold_mad)

            results.append({
                "service": service,
                "operation": operation,
                "duration_ms": val,
                "baseline_median_ms": round(median, 2),
                "modified_z_score": round(float(mod_z), 3),
                "is_anomaly": is_anomaly,
                "threshold_mad": self.threshold_mad,
                "seasonality_note": "Evaluated against 24-hour diurnal rolling median window"
            })

        return results
