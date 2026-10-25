# AI & Machine Learning Integration Deep Dive

## Architecture: Hybrid Statistical ML + Pre-trained LLM

The AI subsystem consists of two complementary layers:
1. **Statistical ML Engine (`ml/`)**: Runs locally on incoming telemetry with sub-millisecond execution times.
2. **Pre-trained LLM API Integration (`ml/llm_engine.py`)**: Queried on demand during active incident triage.

---

## Statistical ML Modules (11 Total)

1. `latency_anomaly.py`: Calculates rolling exponential moving average (EMA) and standard deviation; flags z-score $> 3.0$.
2. `dependency_anomaly.py`: Constructs service call graph; detects unexpected RPC edge additions.
3. `error_spike.py`: Detects sudden step changes in error rates using Poisson process estimation.
4. `trace_anomaly.py`: Evaluates whole-trace structural graph complexity against historical baselines.
5. `performance_regression.py`: Compares latency distributions between deployment versions using Kolmogorov-Smirnov tests.
6. `slow_span_predictor.py`: Predicts whether an in-flight trace will breach SLO based on early span durations.
7. `dynamic_sampling.py`: Dynamically increases sampling rate for services currently exhibiting anomalous behavior.
8. `sampling_recommendation.py`: Recommends budget-optimized sampling percentages per endpoint.
9. `semantic_search.py`: Generates vector embeddings for span error messages and exception stack traces.
10. `root_cause.py`: Causal graph traversal prioritizing deepest downstream failed nodes.
11. `llm_engine.py`: Structured prompt builder and output parser.

---

## LLM Integration & Prompt Guardrails

- **Model Used**: External pre-trained LLM API (OpenAI GPT-4o-mini / Claude 3.5 Sonnet)
- **Zero Custom ML Training**: No custom neural networks were trained; pre-trained foundation models are accessed strictly via API.
- **Prompt Guardrails**:
  - All span attributes pass through the PII redaction engine before prompt assembly.
  - System prompt enforces strict JSON schema output (`{ "summary": str, "root_cause": str, "remediation": [str] }`).
  - Temperature set to `0.1` for maximum determinism.
