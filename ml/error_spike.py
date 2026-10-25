"""
Error-Spike Detection using CUSUM Change-Point Analysis and Poisson Rate Tests.
"""

from typing import List, Dict, Any
import numpy as np
from scipy import stats

class ErrorSpikeDetector:
    def __init__(self, drift_k: float = 0.05, threshold_h: float = 5.0):
        self.drift_k = drift_k
        self.threshold_h = threshold_h

    def detect_error_spike(
        self,
        service: str,
        baseline_error_counts: List[int],
        recent_error_counts: List[int],
        window_size: int = 10
    ) -> Dict[str, Any]:
        """
        Runs CUSUM change-point test and Poisson rate hypothesis testing
        comparing recent error occurrences against historical baseline.
        """
        baseline_mean = float(np.mean(baseline_error_counts)) if baseline_error_counts else 0.1
        recent_mean = float(np.mean(recent_error_counts)) if recent_error_counts else 0.0

        # One-sided tabular CUSUM for upward error rate shifts
        s_pos = 0.0
        max_s = 0.0
        change_point_idx = -1

        for idx, count in enumerate(recent_error_counts):
            # Deviation from expected baseline rate minus allowable slack k
            s_pos = max(0.0, s_pos + (count - baseline_mean - self.drift_k))
            if s_pos > max_s:
                max_s = s_pos
            if s_pos >= self.threshold_h and change_point_idx == -1:
                change_point_idx = idx

        is_spike = bool(max_s >= self.threshold_h)

        # Poisson exact test (or approximate z-test for counts)
        total_recent = sum(recent_error_counts)
        expected_recent = baseline_mean * len(recent_error_counts)
        # Poisson survival function (P(X >= total_recent))
        p_value = float(stats.poisson.sf(total_recent - 1, expected_recent)) if expected_recent > 0 else 1.0

        return {
            "service": service,
            "is_error_spike": is_spike,
            "cusum_statistic": round(max_s, 3),
            "threshold": self.threshold_h,
            "change_point_index": change_point_idx,
            "baseline_mean_errors": round(baseline_mean, 2),
            "recent_mean_errors": round(recent_mean, 2),
            "poisson_p_value": round(p_value, 5)
        }
