# Tech Stack & Tooling

## Sandbox / repo ingestion
- Isolated container per job (locked-down, no network egress needed once clone is done since analysis is static-only)
- Shallow clone (`--depth=1`) to minimize clone time and size
- Resource limits (CPU/memory/disk/time) to guard against oversized or malicious repos
- Note: since execution is static-only (no running of cloned code), isolation requirements are lighter than a full code-execution sandbox — a locked-down container is sufficient; no need for gVisor/Firecracker-grade isolation

## Static analysis
- **tree-sitter** as the universal parsing layer — one library, broad grammar support across Python, TS/TSX, JS/JSX, Go, Rust
- Per-language extraction targets:
  - File tree / module boundaries
  - Imports / dependency graph
  - Function & class signatures
  - Exported symbols / public API surface
  - Entry points (main functions, CLI entry, server bootstrap, etc.)
- Output: a structured "repo skeleton" (JSON/intermediate representation) — this is the primary context object passed to the LLM stages, not raw file contents

## LLM inference — BYOK (Groq only)
- User provides their own Groq API key
- Any model available on Groq can be selected
- User sets a **default model preference**, overridable per run
- Per-run flow:
  1. Estimate token usage from skeleton size (before any LLM call)
  2. Display estimated cost using Groq's published per-token pricing for the selected model
  3. Require explicit confirmation before running
  4. Stream live progress / token usage during generation (Groq's speed makes this a good UX moment)
- Hard cap on max tokens per run (configurable) to protect user's key/balance from runaway jobs

## Doc generation pipeline (LLM calls)
- Parallelized per-file/per-module summarization calls (maximize throughput on Groq)
- Synthesis pass: merges module summaries into the structured doc template
- Template adapts based on detected project type (library / web app / CLI / other)

## Rendering & storage
- Generated docs stored as structured content (e.g., per-section JSON/Markdown) rather than flat HTML, so the site can render navigation, search, etc.
- Docs site: sidebar navigation, search, syntax-highlighted code refs, optionally auto-generated diagrams (e.g., Mermaid) for architecture/module relationships
- Served per-repo (e.g., path or subdomain per generated doc set)

## Implementation stack (decided)
- **Backend: FastAPI, Python for everything except frontend**
  - Sandbox/ingestion, static analysis, estimator, generation, and rendering services all in Python
  - tree-sitter's Python bindings cover all 5 target languages, so no need for a second runtime on the backend
  - FastAPI serves the API layer (submit repo, job status, settings, doc retrieval)
- **Frontend: Next.js**
  - Docs site + product UI (landing, dashboard, generated docs viewer, sidebar/search)
  - Talks to the FastAPI backend over REST (or GraphQL if preferred later)
- Job orchestration: queue-based worker system (Python-native, e.g. Celery/RQ/Arq) for sandboxed clone + analysis + generation jobs
- Storage: object storage for generated doc content + a DB for metadata (repo info, job status, user's model preference, etc.)
