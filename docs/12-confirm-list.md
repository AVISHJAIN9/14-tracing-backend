# Items Requiring Developer Confirmation [CONFIRM WITH DEVELOPER]

| No. | Category | Decision / Topic | Inferred Assumption in Docs | Developer Confirmation Action |
| :---: | :--- | :--- | :--- | :--- |
| 1 | AI Integration | LLM Provider & Key | Assumed OpenAI GPT-4o-mini or Anthropic Claude API for incident postmortems. | Confirm target provider, model tier, and API key environment setup. |
| 2 | Telemetry Storage | ClickHouse vs SQLite | Code contains dual SQLite async harness and ClickHouse schema models. | Confirm whether production environment targets self-hosted ClickHouse or managed ClickHouse Cloud. |
| 3 | Tail Sampling Window | 30-Second Buffer Duration | Assumed default 30-second active window for incomplete traces before evaluation. | Confirm if production SLO requires a longer window for long-running workflows. |
| 4 | Deployment Target | Container Orchestrator | Configured for Docker Compose; production blueprint targets Kubernetes. | Confirm target cloud provider (AWS EKS, GCP GKE, or bare-metal). |
