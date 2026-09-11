# Wovn

Generate a documentation website from a GitHub repository you can access.

Wovn signs you in with GitHub, shallow-clones the repo (public or private), analyzes it with tree-sitter (Python, TypeScript/TSX, JavaScript/JSX, Go, Rust), estimates Groq cost, then — after you confirm — uses **your Groq API key** to write a searchable docs site. Cloned code is never executed.

## Requirements

- Python 3.11+ (3.12 recommended)
- [uv](https://docs.astral.sh/uv/)
- Node 18+ and [pnpm](https://pnpm.io/)
- A [Groq API key](https://console.groq.com/keys)
- A GitHub OAuth App (steps below)

## Clone

```bash
git clone https://github.com/JayTheCoder77/wovn.git
cd wovn
```

## 1. GitHub OAuth App

Create an OAuth App at [github.com/settings/developers](https://github.com/settings/developers) → **OAuth Apps** → **New OAuth App**:

| Field | Value |
|---|---|
| Homepage URL | `http://localhost:3000` |
| Authorization callback URL | `http://localhost:8000/auth/github/callback` |

Use **`localhost` everywhere**, not `127.0.0.1`. Browsers treat those as different sites, so a session cookie set on `127.0.0.1:8000` will not be sent from `localhost:3000` and `/auth/me` will return 401 after login.

Scopes requested at runtime: `read:user` and `repo`.

Copy the client ID and client secret.

## 2. Environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
WOVN_SECRET_KEY=change-me-to-a-long-random-string
WOVN_DATA_DIR=./data
WOVN_CORS_ORIGINS=http://localhost:3000
WOVN_WEB_ORIGIN=http://localhost:3000
WOVN_DATABASE_URL=sqlite:///data/wovn.db
WOVN_GITHUB_CALLBACK_URL=http://localhost:8000/auth/github/callback
WOVN_GITHUB_CLIENT_ID=your-oauth-client-id
WOVN_GITHUB_CLIENT_SECRET=your-oauth-client-secret
WOVN_MULTI_AGENT=true
```

Do not commit `.env`. Rotating `WOVN_SECRET_KEY` invalidates stored Groq keys and GitHub tokens.

## 3. API (port 8000)

From the repo root:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Check [http://localhost:8000/health](http://localhost:8000/health). Schema migrations run on API startup (`alembic upgrade head`).

## 4. Web (port 3000)

In a second terminal:

```bash
cd apps/web
pnpm install
pnpm dev
```

Open **[http://localhost:3000](http://localhost:3000)** (not `127.0.0.1:3000`).

## 5. Use the app

1. Sign in with GitHub.
2. Open **Settings**, paste your Groq API key, save.
3. On the home page, paste `https://github.com/owner/repo` or pick a repo from the GitHub list.
4. Wait for static analysis (no Groq tokens yet).
5. Review the estimate, confirm generation.
6. Open the docs site when the job completes.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Analyze a local folder without Groq:

```bash
wovn-analyze ./path/to/repo
```

## Notes

- `WOVN_MULTI_AGENT=false` uses the older summarize → synthesize path.
- Local data lives under `data/` (SQLite, clones, job artifacts).
- Docs URLs are `/docs/<job-id>` and are visible only to the owning signed-in user.

## Troubleshooting

| Symptom | Fix |
|---|---|
| GitHub callback 302, then `/auth/me` 401 | You mixed `localhost` and `127.0.0.1`. Align OAuth callback, `.env`, and the browser URL on `localhost`. |
| `GitHub OAuth is not configured` | Set `WOVN_GITHUB_CLIENT_ID` and `WOVN_GITHUB_CLIENT_SECRET`, restart the API. |
| Clone: repository not found | Re-sign in so a fresh `repo`-scoped token is stored; confirm you can open the GitHub URL while logged in. |
| Confirm blocked / Groq errors | Add a Groq key in Settings; raise `max_tokens` if the estimate exceeds the cap. |
