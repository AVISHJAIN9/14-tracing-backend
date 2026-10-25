"""
Intelligent Tracing ML API Endpoints.
Exposes ML-backed anomaly detection, latency change points, and error-spike models.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from api.deps import get_tenant_id

# Ensure ml package is discoverable
cur = Path(__file__).resolve()
while cur.parent != cur:
    if (cur / "ml").is_dir():
        ml_path = str(cur / "ml")
        if ml_path not in sys.path:
            sys.path.insert(0, ml_path)
        break
    cur = cur.parent

from trace_anomaly import TraceAnomalyDetector
from latency_anomaly import LatencyAnomalyDetector
from error_spike import ErrorSpikeDetector
from root_cause import RootCauseRanker
from dependency_anomaly import DependencyAnomalyDetector
from performance_regression import PerformanceRegressionDetector
from semantic_search import SemanticTraceSearchEngine
from slow_span_predictor import SlowSpanPredictor
from sampling_recommendation import SamplingRecommender
from dynamic_sampling import DynamicSamplingOptimizer

router = APIRouter(prefix="/ml", tags=["intelligent-tracing-ml"])
semantic_engine = None
dynamic_optimizer = DynamicSamplingOptimizer()

def get_semantic_engine() -> SemanticTraceSearchEngine:
    global semantic_engine
    if semantic_engine is None:
        semantic_engine = SemanticTraceSearchEngine()
    return semantic_engine

slow_span_model = SlowSpanPredictor()

class TraceBatchRequest(BaseModel):
    traces: List[Dict[str, Any]]

class LatencyAnomalyRequest(BaseModel):
    service: str
    operation: str
    history_durations_ms: List[float]
    current_durations_ms: List[float]
    threshold_mad: float = 3.0

class ErrorSpikeRequest(BaseModel):
    service: str
    baseline_error_counts: List[int]
    recent_error_counts: List[int]

class RootCauseRequest(BaseModel):
    spans: List[Dict[str, Any]]
    critical_path_ids: List[str] = []
    service_baselines_ms: Dict[str, float] = {}

class DependencyAnomalyRequest(BaseModel):
    baseline_edges: List[Dict[str, Any]]
    current_edges: List[Dict[str, Any]]
    latency_threshold_ratio: float = 1.75
    volume_threshold_ratio: float = 2.0

class PerformanceRegressionRequest(BaseModel):
    baseline_durations_ms: List[float]
    canary_durations_ms: List[float]
    alpha: float = 0.05

@router.post("/anomalies/traces")
async def detect_trace_anomalies(
    payload: TraceBatchRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    if not payload.traces:
        return {"anomalies": [], "count": 0}

    detector = TraceAnomalyDetector(contamination=0.1)
    results = detector.predict(payload.traces)
    anomalies = [r for r in results if r["is_anomaly"]]

    return {
        "tenant_id": tenant_id,
        "results": results,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies)
    }

@router.post("/anomalies/latency")
async def detect_latency_anomalies(
    payload: LatencyAnomalyRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    detector = LatencyAnomalyDetector(threshold_mad=payload.threshold_mad)
    detections = detector.detect_latency_anomalies(
        service=payload.service,
        operation=payload.operation,
        history_durations_ms=payload.history_durations_ms,
        current_durations_ms=payload.current_durations_ms
    )

    anomalies = [d for d in detections if d["is_anomaly"]]
    return {
        "tenant_id": tenant_id,
        "service": payload.service,
        "operation": payload.operation,
        "detections": detections,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies)
    }

@router.post("/anomalies/error-spikes")
async def detect_error_spikes(
    payload: ErrorSpikeRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    detector = ErrorSpikeDetector()
    analysis = detector.detect_error_spike(
        service=payload.service,
        baseline_error_counts=payload.baseline_error_counts,
        recent_error_counts=payload.recent_error_counts
    )

    return {
        "tenant_id": tenant_id,
        **analysis
    }

@router.post("/root-cause/rank")
async def rank_root_causes(
    payload: RootCauseRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    ranked = RootCauseRanker.rank_root_causes(
        spans=payload.spans,
        critical_path_ids=payload.critical_path_ids,
        service_baselines_ms=payload.service_baselines_ms
    )
    return {
        "tenant_id": tenant_id,
        "ranked_candidates": ranked,
        "count": len(ranked)
    }

@router.post("/anomalies/dependencies")
async def detect_dependency_anomalies(
    payload: DependencyAnomalyRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    anomalies = DependencyAnomalyDetector.detect_dependency_anomalies(
        baseline_edges=payload.baseline_edges,
        current_edges=payload.current_edges,
        latency_threshold_ratio=payload.latency_threshold_ratio,
        volume_threshold_ratio=payload.volume_threshold_ratio
    )
    return {
        "tenant_id": tenant_id,
        "anomalies": anomalies,
        "count": len(anomalies)
    }

@router.post("/regressions/performance")
async def detect_performance_regression(
    payload: PerformanceRegressionRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    result = PerformanceRegressionDetector.detect_regression(
        baseline_durations_ms=payload.baseline_durations_ms,
        canary_durations_ms=payload.canary_durations_ms,
        alpha=payload.alpha
    )
    return {
        "tenant_id": tenant_id,
        **result
    }

class SemanticSearchRequest(BaseModel):
    query: str
    traces: List[Dict[str, Any]]
    top_k: int = 5

@router.post("/semantic-search")
async def semantic_trace_search(
    payload: SemanticSearchRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    engine = get_semantic_engine()
    ranked = engine.rank_traces(query=payload.query, traces=payload.traces, top_k=payload.top_k)
    return {
        "tenant_id": tenant_id,
        "query": payload.query,
        "results": ranked,
        "count": len(ranked)
    }

class TrainSlowSpanRequest(BaseModel):
    spans: List[Dict[str, Any]]
    slow_threshold_ms: float = 100.0

@router.post("/predictions/slow-spans/train")
async def train_slow_span_model(
    payload: TrainSlowSpanRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    metrics = slow_span_model.train_and_evaluate(
        spans=payload.spans,
        slow_threshold_ms=payload.slow_threshold_ms
    )
    return {
        "tenant_id": tenant_id,
        "metrics": metrics
    }

class PredictSlowSpanRequest(BaseModel):
    span: Dict[str, Any]

@router.post("/predictions/slow-spans/predict")
async def predict_slow_span(
    payload: PredictSlowSpanRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    prob = slow_span_model.predict_slow_probability(payload.span)
    return {
        "tenant_id": tenant_id,
        "slow_probability": round(prob, 4),
        "is_predicted_slow": bool(prob >= 0.5)
    }

class SamplingRecommendationRequest(BaseModel):
    service_telemetry: List[Dict[str, Any]]
    target_spans_per_second: float = 2000.0

@router.post("/sampling/recommendations")
async def get_sampling_recommendations(
    payload: SamplingRecommendationRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    recs = SamplingRecommender.recommend_sampling_policies(
        service_telemetry=payload.service_telemetry,
        target_spans_per_second=payload.target_spans_per_second
    )
    return {
        "tenant_id": tenant_id,
        **recs
    }

class DynamicOptimizeRequest(BaseModel):
    service_telemetry: List[Dict[str, Any]]
    target_spans_per_second: float = 2000.0

@router.post("/sampling/dynamic-optimize")
async def dynamic_sampling_optimization(
    payload: DynamicOptimizeRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    from api.routes.sampling import _TENANT_SAMPLING_RULES
    res = dynamic_optimizer.optimize_and_apply(
        service_telemetry=payload.service_telemetry,
        apply_to_registry=_TENANT_SAMPLING_RULES,
        tenant_id=tenant_id
    )
    return {
        "tenant_id": tenant_id,
        **res
    }

from llm_engine import LLMTraceEngine, StructuredTraceQuery

_llm_engine_instance = None

def get_llm_engine() -> LLMTraceEngine:
    global _llm_engine_instance
    if _llm_engine_instance is None:
        _llm_engine_instance = LLMTraceEngine()
    return _llm_engine_instance

class TraceSummarizeRequest(BaseModel):
    trace: Dict[str, Any]

@router.post("/summarize/trace")
async def summarize_trace_endpoint(
    payload: TraceSummarizeRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    engine = get_llm_engine()
    if not engine.is_configured():
        raise HTTPException(status_code=503, detail="LLM_NOT_CONFIGURED")
    try:
        summary = engine.summarize_trace(payload.trace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "tenant_id": tenant_id,
        "summary": summary,
        "model": engine.model_name
    }

class IncidentSummarizeRequest(BaseModel):
    traces: List[Dict[str, Any]]
    incident_title: str

@router.post("/summarize/incident")
async def summarize_incident_endpoint(
    payload: IncidentSummarizeRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    engine = get_llm_engine()
    if not engine.is_configured():
        raise HTTPException(status_code=503, detail="LLM_NOT_CONFIGURED")
    try:
        summary = engine.summarize_incident(payload.traces, payload.incident_title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "tenant_id": tenant_id,
        "summary": summary,
        "model": engine.model_name
    }

class NLQueryRequest(BaseModel):
    query: str

@router.post("/query/natural-language")
async def natural_language_query_endpoint(
    payload: NLQueryRequest,
    tenant_id: str = Depends(get_tenant_id)
) -> Dict[str, Any]:
    engine = get_llm_engine()
    if not engine.is_configured():
        raise HTTPException(status_code=503, detail="LLM_NOT_CONFIGURED")
    try:
        structured = engine.parse_natural_language_query(payload.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "tenant_id": tenant_id,
        "query": payload.query,
        "structured_query": structured.model_dump(),
        "model": engine.model_name
    }




