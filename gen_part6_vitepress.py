import os, json

root_dir = "/Users/avishjain/avishjain9-repos/14-tracing-backend"
docs_dir = os.path.join(root_dir, "docs")
vp_dir = os.path.join(docs_dir, ".vitepress")
theme_dir = os.path.join(vp_dir, "theme")
os.makedirs(theme_dir, exist_ok=True)

# docs/index.md
with open(os.path.join(docs_dir, "index.md"), "w") as f:
    f.write("""---
layout: home

hero:
  name: "14-Tracing-Backend"
  text: "Distributed Tracing & Observability Intelligence Suite"
  tagline: "OpenTelemetry OTLP ingestion, tail-based adaptive sampling, span DAG critical path engine, and pre-trained LLM incident triage."
  actions:
    - theme: brand
      text: Project Overview
      link: /00a-project-analysis
    - theme: alt
      text: 2-Minute Pitch
      link: /00b-project-pitch
    - theme: alt
      text: System Design
      link: /system-design/

features:
  - title: "F1: OpenTelemetry OTLP Ingest"
    details: "High-throughput OTLP Protobuf and JSON collector with non-blocking ring buffer, backpressure load-shedding, and PII scrubbing."
    link: /features/F1-otlp-collector
  - title: "F2: Tail-Based Adaptive Sampling"
    details: "Sliding-window buffer keeping 100% of errors and p99 latency regressions while downsampling nominal traces to reduce storage costs by 75%."
    link: /features/F2-adaptive-sampling
  - title: "F3: Span DAG & Critical Path Engine"
    details: "Topological graph traversal computing the true blocking critical execution path across distributed services with clock-drift compensation."
    link: /features/F3-span-dag-critical-path
  - title: "F4: Statistical ML Anomaly Engine"
    details: "Eleven specialized anomaly detection modules evaluating latency distributions, topology shifts, and causal root-cause attribution."
    link: /features/F4-ml-anomaly-root-cause
  - title: "F5: Pre-trained LLM Incident Postmortems"
    details: "Zero-shot prompt integration transforming complex span dependency graphs into plain-English incident postmortems and remediation advice."
    link: /features/F5-llm-incident-summary
  - title: "High-Scale Columnar Architecture"
    details: "ClickHouse MergeTree storage design handling 150,000 spans/sec with 6x-10x compression and sub-second analytical aggregations."
    link: /system-design/14.5-databases-and-storage
---
""")

# docs/README.md
with open(os.path.join(docs_dir, "README.md"), "w") as f:
    f.write("""# Documentation Index & Reading Guide

Welcome to the official interview-ready documentation for **14-Tracing-Backend**.

## Reading Order

1. [Project Type & Classification](./00-project-type.md)
2. [Full Project Analysis & Trace Matrix](./00a-project-analysis.md)
3. [Project Pitch (30s & 2min Spoken Scripts)](./00b-project-pitch.md)
4. [Project Map & Dependency Inventory](./00-project-map.md)
5. [Feature Inventory](./01-features.md)
6. [Step-by-Step Build Order](./02-build-order.md)
7. [Complete API Reference](./03-api-reference.md)
8. [Technology Choices & Exhaustive Comparisons](./04-tech-comparisons.md)
9. [Architecture & Scalability](./05-architecture.md)
10. [Security Audit & OWASP Top 10](./06-security.md)
11. [AI & ML Integration Deep Dive](./07-ai-integration.md)
12. [Quality Engineering & Operations](./08-quality-and-ops.md)
13. [Interview Q&A (150+ Questions)](./09-interview-qa.md)
14. [Gaps & Roadmap Improvements](./10-gaps-and-improvements.md)
15. [Technical Glossary](./11-glossary.md)
16. [Confirm List](./12-confirm-list.md)
17. [Master Checklist (All 275 Items)](./13-master-checklist.md)
18. [Say It Out Loud: Spoken Scripts & Rehearsal](./14-say-it-out-loud.md)
19. [System Design Deep Dive](./system-design/)
""")

# .vitepress/config.mjs
with open(os.path.join(vp_dir, "config.mjs"), "w") as f:
    f.write("""import { defineConfig } from 'vitepress';
import { withMermaid } from 'vitepress-plugin-mermaid';

export default withMermaid(
  defineConfig({
    title: '14-Tracing-Backend',
    description: 'High-throughput OpenTelemetry distributed tracing and observability intelligence platform.',
    appearance: 'dark',
    base: '/',
    themeConfig: {
      nav: [
        { text: 'Guide', link: '/00a-project-analysis' },
        { text: 'Features', link: '/01-features' },
        { text: 'API Reference', link: '/03-api-reference' },
        { text: 'System Design', link: '/system-design/' },
        { text: 'Interview Q&A', link: '/09-interview-qa' },
        { text: 'Checklist', link: '/13-master-checklist' }
      ],
      sidebar: [
        {
          text: 'Project Overview',
          items: [
            { text: 'Project Type', link: '/00-project-type' },
            { text: 'Project Analysis', link: '/00a-project-analysis' },
            { text: 'Project Pitch', link: '/00b-project-pitch' },
            { text: 'Project Map', link: '/00-project-map' }
          ]
        },
        {
          text: 'Features',
          items: [
            { text: 'Feature Inventory', link: '/01-features' },
            { text: 'Build Order', link: '/02-build-order' },
            { text: 'API Reference', link: '/03-api-reference' },
            { text: 'Tech Comparisons', link: '/04-tech-comparisons' }
          ]
        },
        {
          text: 'Architecture & Security',
          items: [
            { text: 'Architecture', link: '/05-architecture' },
            { text: 'Security Audit', link: '/06-security' },
            { text: 'AI & ML Integration', link: '/07-ai-integration' },
            { text: 'Quality & Operations', link: '/08-quality-and-ops' }
          ]
        },
        {
          text: 'System Design Deep Dive',
          items: [
            { text: 'System Design Overview', link: '/system-design/' },
            { text: '14.1 Capacity Estimation', link: '/system-design/14.1-requirements-and-estimation' },
            { text: '14.5 Columnar Storage', link: '/system-design/14.5-databases-and-storage' },
            { text: 'Architecture Decisions (ADR)', link: '/system-design/decisions' }
          ]
        },
        {
          text: 'Interview & Quality',
          items: [
            { text: 'Interview Q&A (150+)', link: '/09-interview-qa' },
            { text: 'Gaps & Improvements', link: '/10-gaps-and-improvements' },
            { text: 'Glossary', link: '/11-glossary' },
            { text: 'Confirm List', link: '/12-confirm-list' },
            { text: 'Master Checklist (275)', link: '/13-master-checklist' },
            { text: 'Say It Out Loud', link: '/14-say-it-out-loud' }
          ]
        }
      ],
      search: {
        provider: 'local'
      },
      outline: [2, 3]
    },
    mermaid: {
      theme: 'dark'
    },
    vite: {
      optimizeDeps: {
        include: ['mermaid', 'fastdom', 'fastdom/extensions/fastdom-promised.js']
      },
      ssr: {
        noExternal: ['mermaid', 'vitepress-plugin-mermaid', 'fastdom']
      }
    }
  })
);
""")

# .vitepress/theme/index.js
with open(os.path.join(theme_dir, "index.js"), "w") as f:
    f.write("""import DefaultTheme from 'vitepress/theme';
import './custom.css';

export default {
  ...DefaultTheme
};
""")

# .vitepress/theme/custom.css
with open(os.path.join(theme_dir, "custom.css"), "w") as f:
    f.write(""":root {
  --vp-c-brand: #38bdf8;
  --vp-c-brand-light: #7dd3fc;
  --vp-c-brand-dark: #0284c7;
}

.dark {
  --vp-c-bg: #000000 !important;
  --vp-c-bg-alt: #000000 !important;
  --vp-c-bg-elv: #0a0a0a !important;
  --vp-c-bg-soft: #0a0a0a !important;
  --vp-sidebar-bg-color: #000000 !important;
  --vp-c-border: #222222 !important;
  --vp-c-divider: #222222 !important;
}

html.dark body {
  background-color: #000000 !important;
  color: #f1f5f9;
}
""")

# package.json at root of 14-tracing-backend
pkg_path = os.path.join(root_dir, "package.json")
pkg_data = {
    "name": "14-tracing-backend",
    "version": "1.0.0",
    "private": True,
    "scripts": {
        "docs:dev": "vitepress dev docs",
        "docs:build": "vitepress build docs",
        "docs:preview": "vitepress preview docs"
    },
    "devDependencies": {
        "vitepress": "^1.6.3",
        "mermaid": "^11.4.1",
        "vitepress-plugin-mermaid": "^2.0.17"
    }
}
with open(pkg_path, "w") as f:
    json.dump(pkg_data, f, indent=2)

print("Part 6 VitePress configuration written successfully.")
