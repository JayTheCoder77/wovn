from pathlib import Path

from analysis.classifier import classify
from analysis.skeleton_builder import build_skeleton
from doc_schema.models import ProjectType
from estimator.estimate import estimate_job
from estimator.pricing import DEFAULT_MODEL, estimate_cost_usd
from generation.modules import group_files


def write_sample(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["fastapi"]
""",
        encoding="utf-8",
    )
    (root / "app.py").write_text(
        """
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}
""",
        encoding="utf-8",
    )
    pkg = root / "demo"
    pkg.mkdir()
    (pkg / "models.py").write_text(
        """
class Item:
    def __init__(self, name: str):
        self.name = name
""",
        encoding="utf-8",
    )


def test_skeleton_and_classifier(tmp_path: Path):
    write_sample(tmp_path)
    skeleton = build_skeleton(tmp_path, repo_url="https://github.com/acme/demo", root_name="demo")
    assert skeleton.file_count >= 2
    assert any(lang.value == "python" for lang in skeleton.languages)
    project_type, signals = classify(skeleton)
    assert project_type in {ProjectType.web_app, ProjectType.service, ProjectType.general}
    assert "scores" in signals


def test_cli_classifier(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "tool"
version = "0.1.0"
[project.scripts]
tool = "tool.cli:main"
""",
        encoding="utf-8",
    )
    (tmp_path / "cli.py").write_text(
        """
import click

@click.command()
def main():
    pass

if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    skeleton = build_skeleton(tmp_path, repo_url="https://github.com/acme/tool", root_name="tool")
    project_type, _ = classify(skeleton)
    assert project_type == ProjectType.cli


def test_estimator_positive(tmp_path: Path):
    write_sample(tmp_path)
    skeleton = build_skeleton(tmp_path, repo_url="https://github.com/acme/demo", root_name="demo")
    estimate = estimate_job(skeleton, DEFAULT_MODEL)
    assert estimate["summarization_calls"] >= 1
    assert estimate["estimated_cost_usd"] >= 0
    assert estimate["file_count"] == skeleton.file_count
    groups = group_files(skeleton.files)
    assert groups


def test_pricing_math():
    cost = estimate_cost_usd("openai/gpt-oss-20b", 1_000_000, 1_000_000)
    assert cost == 0.375
