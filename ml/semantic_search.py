"""
Semantic Trace Search using Sentence-Transformers Vector Embeddings.
Embeds textual trace signatures using all-MiniLM-L6-v2 and computes cosine similarity ranking.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

class SemanticTraceSearchEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    @staticmethod
    def build_trace_signature(trace: Dict[str, Any]) -> str:
        """
        Synthesizes a rich semantic textual representation of the trace execution DAG.
        """
        tid = trace.get("trace_id", "")
        svc = trace.get("root_service_name") or trace.get("root_service", "unknown")
        op = trace.get("root_name", "operation")
        dur_ms = float(trace.get("duration_nanos", 0)) / 1_000_000.0
        err_count = trace.get("error_count", 0)

        spans_summary = []
        for s in trace.get("spans", []):
            s_name = s.get("name", "")
            s_svc = s.get("service_name", "")
            status = s.get("status_code", "OK")
            spans_summary.append(f"{s_svc}:{s_name}[{status}]")

        flow_str = " -> ".join(spans_summary[:8])
        return (
            f"Trace {tid} on service {svc} executing {op}. "
            f"Duration: {dur_ms:.1f}ms. Errors: {err_count}. "
            f"Call chain: {flow_str}."
        )

    def encode(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def rank_traces(
        self,
        query: str,
        traces: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        if not traces:
            return []

        signatures = [self.build_trace_signature(t) for t in traces]
        trace_embeddings = self.encode(signatures)
        query_embedding = self.encode([query])[0]

        # Cosine similarity for normalized embeddings is simply the dot product
        similarities = np.dot(trace_embeddings, query_embedding)

        ranked_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in ranked_indices:
            score = float(similarities[idx])
            t = traces[idx]
            results.append({
                "trace_id": t.get("trace_id", ""),
                "similarity_score": round(score, 4),
                "root_service": t.get("root_service_name") or t.get("root_service", ""),
                "root_name": t.get("root_name", ""),
                "signature": signatures[idx]
            })

        return results
