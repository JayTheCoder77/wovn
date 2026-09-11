# Architecture & Pipeline

## Stage-by-stage flow

### 1. Ingest
- User submits GitHub repo URL (public repo v1; private repo auth via GitHub OAuth/PAT is a future consideration)
- Shallow clone into an isolated, ephemeral container
- Basic validation: repo size limits, supported language detection, reject unsupported/empty repos

### 2. Static analysis
- Detect languages present (Python / TS / TSX / JS / JSX / Go / Rust)
- Run tree-sitter parsers per file
- Build the **repo skeleton**:
  - File/folder tree
  - Per-file: imports, exported symbols, function/class signatures, docstrings/comments if present
  - Cross-file relationships (import graph, call references where feasible)
  - Detected entry points
- This stage is 100% local/deterministic — no LLM calls, no cost to the user

### 3. Cost/token estimation
- Estimate number of summarization calls (roughly proportional to module/file count)
- Estimate input/output token volume from skeleton size
- Price against the user's selected Groq model (default preference, overridable)
- Present estimate + confirmation gate to the user

### 4. Summarization (parallelized)
- Per-module (or per-file, depending on granularity chosen) LLM calls using the skeleton as context — not raw full file contents, to keep context lean and calls fast
- Parallelized to maximize Groq throughput
- Output: structured per-module summaries (purpose, key exports, dependencies, notable patterns)

### 5. Project-type classification
- Signals derived from the skeleton (entry points, dependency manifests, presence of routes/handlers, CLI argument parsing, package.json/pyproject.toml/Cargo.toml/go.mod contents, etc.) determine project type: library / web app / CLI / service / other
- This classification drives which sections the adaptive template includes (see `04-doc-template.md`)

### 6. Synthesis
- Single (or small number of) synthesis call(s) that merge:
  - Module summaries
  - Project-type classification
  - Skeleton-level structural info
- Produces the final structured document content per the adaptive template

### 7. Render & store
- Structured output converted into the docs site's internal format
- Stored (object storage + metadata DB)
- Docs site renders: nav sidebar, search, code references, diagrams

## Design principle: skeleton-first context
Across every LLM-calling stage, the **skeleton** (not raw file contents) is the primary context object. This keeps:
- Token usage predictable and estimable upfront
- Calls fast (small, focused context per call)
- The pipeline scalable to larger repos without blowing context windows

## Parallelization notes
- Summarization calls are independent per module → safe to parallelize aggressively
- Rate limits on the user's Groq key should be respected (backoff/retry logic needed)
- Synthesis stage depends on all summarization outputs → acts as a join point before final generation
