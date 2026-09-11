# Wovn

Generate a documentation website from a GitHub repository you can access.

Wovn signs you in with GitHub, shallow-clones the repo (public or private via your OAuth token), statically analyzes it with tree-sitter (Python, TypeScript/TSX, JavaScript/JSX, Go, Rust), estimates Groq token cost, then — after you confirm — uses **your Groq API key** to write structured docs.

## v2

Signed-in users, per-user settings/repos/jobs, private clone, ContextPacks, and a **multi-agent** generation path (coordinator + specialists + synthesizer). Set `WOVN_MULTI_AGENT=false` to keep the legacy summarize → synthesize pipeline.

| Question | Decision |
|---|---|
| Auth | GitHub OAuth; HTTP-only `wovn_session` cookie on the API |
| Database | SQLAlchemy 2 + Alembic; SQLite locally (`WOVN_DATABASE_URL`) |
| Secrets | Fernet (`fernet-v1`); rotating `WOVN_SECRET_KEY` invalidates stored Groq and GitHub tokens |
| MVP SQLite | Existing anonymous `jobs` / `settings` rows are **not** migrated. Delete or ignore old `data/wovn.db` |
| Docs URL | `/docs/<job-id>` for the owning user only |
| Isolation | Shallow clone with git hooks disabled; cloned code is never executed |

## GitHub OAuth app

Create an OAuth App on GitHub with:

- Homepage URL: `http://localhost:3000`
- Authorization callback URL: `http://127.0.0.1:8000/auth/github/callback`

Copy the client id and secret into `.env` as `WOVN_GITHUB_CLIENT_ID` and `WOVN_GITHUB_CLIENT_SECRET`. Scopes requested: `read:user` and `repo`.

## Run locally

Requires Python 3.11+ (this repo uses `uv`) and Node 18+ with `pnpm`.

```bash
# API
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
# fill GitHub OAuth client id/secret
uvicorn api.main:app --reload --port 8000

# Web
cd apps/web
pnpm install
pnpm dev
```

Open http://localhost:3000, sign in with GitHub, add a Groq key under Settings, register a repo, review the estimate, then confirm generation.

Schema migrations run on API startup (`alembic upgrade head`). To run them yourself:

```bash
alembic upgrade head
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Analyze a local checkout without Groq:

```bash
wovn-analyze ./path/to/repo
```
