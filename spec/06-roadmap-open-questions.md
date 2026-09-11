# Roadmap & Open Questions

## MVP scope (suggested)
1. Public GitHub repos only (no private repo auth yet)
2. Languages: Python, TypeScript/TSX, JavaScript/JSX, Go, Rust
3. One-time snapshot generation only
4. Groq BYOK, default model preference + per-run override
5. Adaptive template: library / web app / CLI / general fallback
6. Docs site with sidebar nav + search (diagrams as a stretch goal for v1)

## Post-MVP candidates
- Private repo support (GitHub OAuth/PAT)
- Incremental re-sync on push (webhook-triggered updates)
- Multi-label project-type classification for monorepos
- Auto-generated architecture/call-graph diagrams (Mermaid)
- Team/collaboration features (shared docs, comments)
- Export generated docs (Markdown/PDF download)

## Open questions to resolve before/during build
- Exact granularity of summarization calls: per-file vs. per-module/folder
- Cross-file relationship depth: how far to trace import/call graphs before cost outweighs value
- Model override persistence: reset to default each run, or remember last override for the session
- Hard token cap default value, and whether it's global or scales with repo size
- Docs site URL scheme: subdomain per repo vs. path-based routing
- Whether to support monorepos with mixed languages/multiple project types in v1 or defer

## Suggested next steps
1. Validate tree-sitter extraction quality across all 5 target languages on a handful of real repos
2. Prototype the skeleton schema (`packages/skeleton-schema`) and get it stable before building generation logic on top
3. Build the cost estimator against real Groq pricing and test estimate accuracy vs. actual run cost
4. Build one end-to-end path (single language, single project type) before generalizing to the adaptive template
