# Adaptive Structured Doc Template

## Principle
The doc template is not fixed — sections included depend on the detected project type. This keeps generated docs relevant instead of forcing every repo into the same shape (e.g., a CLI tool doesn't need an "API Reference" section for HTTP routes).

## Project-type classification signals (from the skeleton)
| Signal | Suggests |
|---|---|
| `package.json` with `bin` field, or Python `console_scripts` entry point, or Go `main.go` with flag parsing, or Rust `clap`/`structopt` usage | CLI tool |
| Route/handler patterns (Express/FastAPI/Flask/Gin/Actix routes) | Web app / service |
| No entry point, exported public API surface, published to a package registry (setup.py/pyproject.toml with `packages`, package.json without `bin`/`main` app) | Library |
| Dockerfile + service routes + no CLI | Backend service |
| Mixed signals | Fallback to a general-purpose default template |

## Common sections (present across all types)
- **Overview** — what the project does, tech stack detected, high-level architecture summary
- **Getting Started** — install/setup instructions (derived from manifest files, README if present)
- **Project Structure** — annotated file/folder tree with module purposes

## Type-specific sections

### Library
- **API Reference** — public functions/classes/exports with signatures and descriptions
- **Usage Examples** — synthesized from function signatures + any existing tests/examples in repo

### Web app / Service
- **Architecture** — component/module relationship diagram
- **API Endpoints** — route list with methods, params, and inferred purpose
- **Data Models** — detected schemas/models (DB models, request/response types)

### CLI tool
- **Commands Reference** — subcommands, flags, arguments
- **Configuration** — config file formats/env vars if detected

### Fallback/General
- **Module Breakdown** — per-module summary without assuming a specific project shape

## Output structure (conceptual schema)
```json
{
  "project_type": "web_app | library | cli | service | general",
  "overview": "...",
  "getting_started": "...",
  "structure": [ { "path": "...", "purpose": "..." } ],
  "sections": [
    { "type": "api_reference", "content": [...] },
    { "type": "architecture", "diagram": "mermaid string", "content": "..." }
  ]
}
```

## Open question
Should classification be single-label (one project type drives the whole template) or multi-label (e.g., a repo can be both "service" and expose a "library" package within the same monorepo, requiring a hybrid template)? Worth revisiting once real repos are tested against the classifier.
