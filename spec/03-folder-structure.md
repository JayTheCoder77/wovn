# Proposed Product Folder Structure

This is a suggested starting layout for the product's own codebase (not the repos being analyzed).

```
wovn/
├── apps/
│   ├── web/                     # Frontend — docs site + product UI (Next.js)
│   │   ├── app/                 # Routes: landing, dashboard, generated docs viewer
│   │   ├── components/          # UI components (nav, search, doc renderer, diagrams)
│   │   └── lib/                 # API client, auth helpers
│   │
│   └── api/                     # Backend API service (FastAPI, Python)
│       ├── routes/              # REST endpoints (submit repo, job status, settings)
│       ├── auth/                # User auth, Groq key storage (encrypted at rest)
│       └── jobs/                # Job orchestration (enqueue, status tracking)
│
├── services/
│   ├── ingest/                  # Repo cloning + sandbox container management
│   │   ├── sandbox/             # Container config, resource limits
│   │   └── clone.py             # Shallow clone logic, validation
│   │
│   ├── analysis/                # Static analysis engine
│   │   ├── parsers/             # tree-sitter integration per language
│   │   │   ├── python.py
│   │   │   ├── typescript.py
│   │   │   ├── javascript.py
│   │   │   ├── go.py
│   │   │   └── rust.py
│   │   ├── skeleton_builder.py  # Builds the unified repo skeleton IR
│   │   └── classifier.py        # Project-type classification logic
│   │
│   ├── estimator/                # Token/cost estimation
│   │   ├── token_counter.py
│   │   └── pricing.py            # Groq model pricing table
│   │
│   ├── generation/                # LLM pipeline
│   │   ├── groq_client.py         # Groq API wrapper (BYOK key handling)
│   │   ├── summarize.py           # Per-module summarization (parallelized)
│   │   ├── synthesize.py          # Final synthesis into doc template
│   │   └── templates/             # Adaptive doc templates (library/webapp/cli/other)
│   │
│   └── renderer/                  # Converts structured doc output → site-ready content
│       ├── markdown_renderer.py
│       └── diagram_gen.py          # Mermaid/diagram generation
│
├── packages/
│   ├── skeleton-schema/            # Shared schema/types for the repo skeleton IR
│   └── doc-schema/                 # Shared schema/types for structured doc output
│
├── infra/
│   ├── docker/                     # Sandbox container images per language
│   └── queue/                      # Job queue config (e.g., worker definitions)
│
└── spec/                           # This spec folder
```

## Notes
- Everything except `apps/web` is Python (FastAPI for the API layer, plain Python for `services/`) — one runtime for ingestion, analysis, estimation, generation, and rendering
- `services/` are designed to be independently scalable workers (ingest, analysis, generation are natural queue-based job stages), invoked by the FastAPI app or a task queue
- `packages/skeleton-schema` and `packages/doc-schema` are defined as Pydantic models on the Python side; since the frontend is Next.js/TypeScript, generate TS types from the FastAPI OpenAPI schema (or Pydantic → JSON Schema → TS) to keep both sides in sync without hand-duplicating types
- Sandbox container images in `infra/docker/` can be per-language or a single multi-language image with tree-sitter grammars pre-installed — worth benchmarking cold-start time for the "speed" positioning
