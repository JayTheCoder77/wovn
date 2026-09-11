from pathlib import Path

from analysis.skeleton_builder import build_skeleton
from estimator.estimate import (
    PROMPT_OVERHEAD_TOKENS,
    SUMMARY_OUTPUT_TOKENS,
    SYNTHESIS_OVERHEAD_TOKENS,
    estimate_job,
)
from estimator.pricing import DEFAULT_MODEL
from estimator.token_counter import count_tokens
from generation.context.packs import (
    MODULE_TOKEN_CAP,
    build_context_packs,
    group_files,
    render_global_pack,
    render_module_pack,
)
from generation.summarize import SYSTEM as SUMMARIZE_SYSTEM
from skeleton_schema.models import FileSkeleton, LanguageName, RepoSkeleton, Snippet, Symbol, SymbolKind

FIXTURE = Path(__file__).parent / "fixtures" / "context_repo"


def _skeleton():
    return build_skeleton(FIXTURE, repo_url="https://github.com/acme/demo", root_name="demo")


def test_cheap_skeleton_fields():
    skeleton = _skeleton()
    assert skeleton.readme_digest
    assert "Tiny FastAPI" in skeleton.readme_digest
    deps = [d.lower() for d in skeleton.manifest_summary.get("dependencies", [])]
    assert any("fastapi" in d for d in deps)
    names = {entry.name for entry in skeleton.public_api}
    assert "health" in names
    mapped = skeleton.test_map.get("test_models.py") or []
    assert "demo/models.py" in mapped


def test_snippets_capture_health_without_whole_file():
    skeleton = _skeleton()
    app = next(f for f in skeleton.files if f.path == "app.py")
    assert app.snippets
    joined = "\n".join(s.text for s in app.snippets)
    assert "def health" in joined
    full = (FIXTURE / "app.py").read_text(encoding="utf-8")
    for snippet in app.snippets:
        assert snippet.text != full
        assert snippet.end_line - snippet.start_line + 1 <= 12


def test_module_pack_includes_provenance_and_snippet_ranges():
    packs = build_context_packs(_skeleton())
    text = "\n".join(render_module_pack(m) for m in packs.modules)
    assert "FILE:" in text or "FILE " in text
    assert "app.py:" in text
    assert any(f.snippets for pack in packs.modules for f in pack.files)


def test_group_files_groups_root_and_folder_files_deterministically():
    files = [
        FileSkeleton(path="api/routes.py", language=LanguageName.python, loc=1),
        FileSkeleton(path="main.py", language=LanguageName.python, loc=1),
        FileSkeleton(path="api/models.py", language=LanguageName.python, loc=1),
    ]

    groups = group_files(files)

    assert [(group.name, [file.path for file in group.files]) for group in groups] == [
        (".", ["main.py"]),
        ("api", ["api/routes.py", "api/models.py"]),
    ]


def test_over_budget_pack_trims_snippets_first():
    symbols = [
        Symbol(name=f"fn_{i}", kind=SymbolKind.function, signature=f"def fn_{i}():", exported=True, line=i + 1)
        for i in range(30)
    ]
    snippets = [
        Snippet(
            path="big.py",
            start_line=1,
            end_line=12,
            text="x" * 200,
            reason="module_doc",
        ),
        Snippet(
            path="big.py",
            start_line=20,
            end_line=31,
            text="y" * 200,
            reason="export",
        ),
        Snippet(
            path="big.py",
            start_line=40,
            end_line=51,
            text="z" * 200,
            reason="entry_point",
        ),
    ]
    file = FileSkeleton(
        path="big.py",
        language=LanguageName.python,
        loc=80,
        symbols=symbols,
        snippets=snippets,
        is_entry_point=True,
    )
    skeleton = RepoSkeleton(
        repo_url="https://github.com/acme/big",
        root_name="big",
        files=[file],
        file_count=1,
        loc=80,
        public_api=[],
        readme_digest="README " * 400,
        manifest_summary={"dependencies": ["fastapi"] * 50},
        tree=["big.py"] * 80,
        import_graph={"big.py": [f"mod{i}" for i in range(40)]},
    )
    packs = build_context_packs(skeleton, module_token_cap=80, global_token_cap=80)
    assert packs.modules[0].trimmed or packs.global_pack.trimmed
    remaining_reasons = [s.reason for f in packs.modules[0].files for s in f.snippets]
    if remaining_reasons:
        assert "module_doc" not in remaining_reasons or remaining_reasons == ["entry_point"]
        if "module_doc" in remaining_reasons:
            raise AssertionError("lowest-priority snippets should be dropped first")


def test_estimator_matches_pack_tokens():
    skeleton = _skeleton()
    packs = build_context_packs(skeleton)
    pack_input = count_tokens(render_global_pack(packs.global_pack)) + sum(
        count_tokens(render_module_pack(m)) for m in packs.modules
    )
    n = len(packs.modules)
    expected_input = (
        pack_input
        + n * PROMPT_OVERHEAD_TOKENS
        + SYNTHESIS_OVERHEAD_TOKENS
        + n * SUMMARY_OUTPUT_TOKENS
    )
    estimate = estimate_job(skeleton, DEFAULT_MODEL, multi_agent=False)
    assert estimate["pack_input_tokens"] == pack_input
    assert estimate["estimated_input_tokens"] == expected_input
    assert estimate["summarization_calls"] == n
    assert estimate["synthesis_calls"] == 1


def test_summarizer_prompt_requires_citations():
    assert "citations" in SUMMARIZE_SYSTEM.lower()
    assert MODULE_TOKEN_CAP > 0
