"""
Slow-Span Prediction using Gradient Boosted Trees.
Trained on historical span features, reporting holdout accuracy, precision, and recall.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

class SlowSpanPredictor:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = HistGradientBoostingClassifier(random_state=random_state, max_iter=100, min_samples_leaf=2)
        self.is_fitted = False
        self.holdout_metrics: Dict[str, float] = {}

    def extract_features(self, span: Dict[str, Any]) -> List[float]:
        svc_hash = float(hash(span.get("service_name", "")) % 1000)
        op_hash = float(hash(span.get("name", "")) % 1000)
        kind_hash = float(hash(span.get("kind", "INTERNAL")) % 100)
        attr_count = float(len(span.get("attributes", {})))
        events_count = float(len(span.get("events", [])))
        links_count = float(len(span.get("links", [])))
        return [svc_hash, op_hash, kind_hash, attr_count, events_count, links_count]

    def train_and_evaluate(
        self,
        spans: List[Dict[str, Any]],
        slow_threshold_ms: float = 100.0,
        test_size: float = 0.2
    ) -> Dict[str, float]:
        if len(spans) < 20:
            raise ValueError("SlowSpanPredictor requires at least 20 historical span samples")

        X = np.array([self.extract_features(s) for s in spans], dtype=float)
        # Binary target: 1 if slow, 0 otherwise
        y = np.array([
            1 if (float(s.get("duration_nanos", 0)) / 1_000_000.0) >= slow_threshold_ms else 0
            for s in spans
        ], dtype=int)

        # Stratified holdout split if multiple classes exist
        strat = y if len(np.unique(y)) > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=strat
        )

        self.model.fit(X_train, y_train)
        self.is_fitted = True

        y_pred = self.model.predict(X_test)

        self.holdout_metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "test_samples": len(y_test),
            "train_samples": len(y_train)
        }
        return self.holdout_metrics

    def predict_slow_probability(self, span: Dict[str, Any]) -> float:
        if not self.is_fitted:
            return 0.5
        x = np.array([self.extract_features(span)], dtype=float)
        prob = self.model.predict_proba(x)[0]
        # Return probability of class 1 (slow)
        return float(prob[1]) if len(prob) > 1 else float(prob[0])
