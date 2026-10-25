"""
Performance Regression Detection using Non-Parametric Mann-Whitney U Hypothesis Testing.
Compares duration distributions between canary/baseline releases, reporting effect sizes and p-values.
"""

from typing import List, Dict, Any
import numpy as np
from scipy import stats

class PerformanceRegressionDetector:
    @staticmethod
    def detect_regression(
        baseline_durations_ms: List[float],
        canary_durations_ms: List[float],
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Executes a two-sided Mann-Whitney U test between baseline and canary durations.
        Calculates Cliff's Delta / Rank-Biserial correlation effect size.
        """
        if not baseline_durations_ms or not canary_durations_ms:
            return {
                "is_regression": False,
                "p_value": 1.0,
                "effect_size": 0.0,
                "u_statistic": 0.0,
                "details": "Insufficient duration samples"
            }

        arr_base = np.array(baseline_durations_ms, dtype=float)
        arr_canary = np.array(canary_durations_ms, dtype=float)

        res = stats.mannwhitneyu(arr_canary, arr_base, alternative="greater")
        u_stat = float(res.statistic)
        p_val = float(res.pvalue)

        # Effect size (Cliff's Delta or Rank Biserial)
        n1 = len(arr_canary)
        n2 = len(arr_base)
        rank_biserial = float((2 * u_stat / (n1 * n2)) - 1.0)

        med_base = float(np.median(arr_base))
        med_canary = float(np.median(arr_canary))
        delta_ms = med_canary - med_base
        delta_pct = (delta_ms / max(med_base, 0.001)) * 100.0

        # Statistically significant degradation: p < alpha and positive effect size
        is_regression = bool(p_val < alpha and rank_biserial > 0.15 and delta_ms > 0)

        return {
            "is_regression": is_regression,
            "p_value": round(p_val, 6),
            "effect_size": round(rank_biserial, 3),
            "u_statistic": round(u_stat, 2),
            "baseline_median_ms": round(med_base, 2),
            "canary_median_ms": round(med_canary, 2),
            "median_delta_ms": round(delta_ms, 2),
            "median_delta_pct": round(delta_pct, 2),
            "significance_level": alpha
        }
