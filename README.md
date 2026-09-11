# Wovn

Generate a documentation website from a public GitHub repository.

Wovn shallow-clones the repo, statically analyzes it with tree-sitter (Python, TypeScript/TSX, JavaScript/JSX, Go, Rust), estimates Groq token cost, then — after you confirm — uses **your Groq API key** to write structured docs.

## MVP decisions (locked for this build)

| Question | Decision |
|---|---|
| Summarization granularity | Group by top-level folder, max 12 files per LLM call |
| Model override persistence | Resets to the saved default on each new job |
| Docs URL scheme | Path-based: `/docs/<job-id>` |
| Project-type labels | Single-label (`library` / `web_app` / `cli` / `service` / `general`) |
| Default token cap | 200,000 tokens per run, adjustable in Settings |
| Isolation | Shallow clone with git hooks disabled; cloned code is never executed |

## Run locally

Requires Python 3.11+ (this repo uses `uv`) and Node 18+ with `pnpm`.

```bash
# API
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
uvicorn api.main:app --reload --port 8000

# Web
cd apps/web
pnpm install
pnpm dev
```

Open http://localhost:3000. Add a Groq key under Settings, paste a public GitHub URL, review the estimate, then confirm generation.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Analyze a local checkout without Groq:

```bash
wovn-analyze ./path/to/repo
```
