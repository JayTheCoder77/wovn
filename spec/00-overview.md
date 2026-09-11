# Wovn — Project Overview

## One-liner
A website where a user provides a GitHub repo link, the repo is cloned in a sandboxed environment, statically analyzed, and an AI (via the user's own Groq API key) generates a structured documentation website — viewable directly on the platform.

## Core value proposition
- **Speed** is the primary differentiator (vs. tools like DeepWiki, Devin's wiki feature, etc.)
- **BYOK (Bring Your Own Key)** — user supplies their own Groq API key, so the platform bears no inference cost
- **Static-analysis only** — no execution of untrusted cloned code, keeping sandboxing lightweight and safe
- **One-time snapshot** — no re-sync/incremental updates on repo pushes (out of scope for v1)

## Target languages (v1)
- Python
- TypeScript (.ts, .tsx)
- JavaScript (.js, .jsx)
- Go
- Rust

## High-level flow
1. User submits a GitHub repo URL
2. Repo is shallow-cloned inside an isolated container
3. Static analysis (tree-sitter based) builds a structural "skeleton" of the codebase
4. Skeleton is used to estimate LLM token usage / cost and shown to the user before running
5. User confirms (using their default Groq model, or overrides per-run)
6. Pipeline runs: per-module summarization (parallelized) → synthesis into a structured doc template
7. Generated docs are rendered and stored, viewable as a docs website on the platform

## Key decisions locked in so far
| Area | Decision |
|---|---|
| Execution model | Static analysis only, no code execution |
| Update model | One-time snapshot (no incremental re-sync) |
| Output format | Structured (adapts by detected project type) |
| Differentiator | Speed |
| Inference | BYOK — Groq only (no OpenRouter) |
| Model selection | User sets a default model preference, overridable per run |
| Languages (v1) | Python, TS/TSX, JS/JSX, Go, Rust |
| Backend stack | FastAPI, Python for everything except frontend |
| Frontend stack | Next.js |
| Product name | Wovn |

## Open questions (not yet decided)
- Exact adaptive template logic (what signals classify "library" vs "web app" vs "CLI")
- Exact skeleton → summarization → synthesis context design per LLM call
- Whether model override persists for the session or resets to saved default each run
- Hard token/cost cap per run
- Monetization model beyond BYOK (subscription for hosting/storage? free tier limits?)
