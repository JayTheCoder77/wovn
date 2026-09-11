from __future__ import annotations

import json
from pathlib import Path

from analysis.skeleton_builder import build_skeleton
from doc_schema.agents import RunPlan
from doc_schema.models import ProjectType
from estimator.estimate import estimate_job
from estimator.pricing import DEFAULT_MODEL
from generation.agents.coordinator import clamp_plan, fallback_plan
from generation.context.packs import build_context_packs
from generation.orchestrator import run_multi_agent

FIXTURE = Path(__file__).parent / "fixtures" / "context_repo"


def _skeleton():
    return build_skeleton(FIXTURE, repo_url="https://github.com/acme/demo", root_name="demo")


class FakeGroq:
    def __init__(self, replies: dict[str, str] | None = None):
        self.kinds: list[str] = []
        self.users: list[str] = []
        self.replies = replies or {}
        self.tokens_used = 0
        self.max_tokens_remaining = 10_000_000

    def kind_of(self, system: str) -> str:
        text = system.lower()
        if "you merge structured" in text or "merge only" in text:
            return "synthesize"
        if "choose which modules" in text or "run plan" in text:
            return "coordinator"
        if "unsupported claims" in text or "missing sections" in text:
            return "critic"
        if "architecture draft" in text:
            return "architecture"
        if "surface draft" in text:
            return "surface"
        if "operations draft" in text:
            return "operations"
        return "summarize"

    async def complete(self, *, system: str, user: str, json_mode: bool = True, max_completion_tokens: int = 2048) -> str:
        kind = self.kind_of(system)
        self.kinds.append(kind)
        self.users.append(user)
        if kind in self.replies:
            return self.replies[kind]
        return self._default(kind)

    def _default(self, kind: str) -> str:
        if kind == "coordinator":
            return json.dumps(
                {
                    "module_names": ["_root", "invented"],
                    "run_architecture": True,
                    "run_surface": True,
                    "run_operations": True,
                    "run_critic": False,
                    "rationale": "test",
                }
            )
        if kind == "architecture":
            return json.dumps(
                {
                    "narrative": "Demo app",
                    "components": [{"name": "app", "role": "http"}],
                    "diagram": "flowchart LR\n  a --> b",
                    "citations": [{"path": "app.py", "line": 1}],
                }
            )
        if kind == "surface":
            return json.dumps(
                {
                    "section_type": "api_endpoints",
                    "title": "HTTP",
                    "content": "health",
                    "items": [{"name": "health"}],
                    "citations": [{"path": "app.py", "line": 18}],
                }
            )
        if kind == "operations":
            return json.dumps(
                {
                    "getting_started": "pip install -e .",
                    "env_var_names": [],
                    "notes": ["python"],
                    "citations": [{"path": "pyproject.toml", "line": 1}],
                }
            )
        if kind == "critic":
            return json.dumps({"unsupported": [], "missing_sections": [], "ok": True})
        if kind == "synthesize":
            return json.dumps(
                {
                    "title": "demo",
                    "overview": "python web app",
                    "getting_started": "pip install",
                    "structure": [{"path": "_root", "purpose": "app"}],
                    "sections": [{"type": "architecture", "title": "Arch", "content": "ok", "diagram": None, "items": []}],
                }
            )
        return json.dumps(
            {
                "purpose": "module",
                "key_exports": [],
                "dependencies": [],
                "notable_patterns": [],
                "citations": [],
            }
        )


def test_clamp_drops_invented_modules_and_fills_empty():
    available = ["_root", "demo"]
    clamped = clamp_plan(
        RunPlan(module_names=["ghost", "demo"], run_architecture=True),
        available,
    )
    assert clamped.module_names == ["demo"]
    filled = clamp_plan(RunPlan(module_names=[]), available)
    assert filled.module_names == available


def test_fallback_plan_enables_critic_only_for_large_repos():
    small = fallback_plan(["_root"], file_count=3)
    large = fallback_plan(["_root"], file_count=21)
    assert small.run_critic is False
    assert large.run_critic is True
    assert small.run_architecture and small.run_surface and small.run_operations


def test_orchestrator_coordinator_runs_first_and_clamps_modules(tmp_path: Path):
    import asyncio

    skeleton = _skeleton()
    packs = build_context_packs(skeleton)
    client = FakeGroq()
    asyncio.run(
        run_multi_agent(
            client,
            skeleton,
            packs,
            ProjectType.web_app,
            artifact_dir=tmp_path,
        )
    )
    assert client.kinds[0] == "coordinator"
    assert "architecture" in client.kinds
    assert "invented" not in json.dumps(client.users)
    assert (tmp_path / "coordinator.json").exists()
    assert (tmp_path / "architecture.json").exists()
    synth_users = [u for k, u in zip(client.kinds, client.users) if k == "synthesize"]
    assert synth_users
    payload = json.loads(synth_users[0])
    assert "architecture" in payload
    assert "surface" in payload
    assert "operations" in payload


def test_parse_failure_uses_fallback(tmp_path: Path):
    import asyncio

    skeleton = _skeleton()
    packs = build_context_packs(skeleton)
    client = FakeGroq(replies={"coordinator": "not-json"})
    asyncio.run(
        run_multi_agent(
            client,
            skeleton,
            packs,
            ProjectType.web_app,
            artifact_dir=tmp_path,
        )
    )
    plan = json.loads((tmp_path / "coordinator.json").read_text(encoding="utf-8"))
    assert set(plan["module_names"]) == {m.name for m in packs.modules}
    assert plan["run_architecture"] is True
    assert plan["run_critic"] is False


def test_critic_false_triggers_one_repair(tmp_path: Path):
    import asyncio

    skeleton = _skeleton()
    packs = build_context_packs(skeleton)
    client = FakeGroq(
        replies={
            "coordinator": json.dumps(
                {
                    "module_names": [packs.modules[0].name],
                    "run_architecture": True,
                    "run_surface": False,
                    "run_operations": False,
                    "run_critic": True,
                    "rationale": "critic",
                }
            ),
            "critic": json.dumps(
                {"unsupported": ["invented route"], "missing_sections": [], "ok": False}
            ),
        }
    )
    asyncio.run(
        run_multi_agent(
            client,
            skeleton,
            packs,
            ProjectType.web_app,
            artifact_dir=tmp_path,
        )
    )
    assert client.kinds.count("critic") == 1
    assert client.kinds.count("synthesize") == 2
    assert "surface" not in client.kinds
    assert "operations" not in client.kinds


def test_run_critic_false_skips_critic_and_repair(tmp_path: Path):
    import asyncio

    skeleton = _skeleton()
    packs = build_context_packs(skeleton)
    client = FakeGroq(
        replies={
            "coordinator": json.dumps(
                {
                    "module_names": [m.name for m in packs.modules],
                    "run_architecture": True,
                    "run_surface": True,
                    "run_operations": True,
                    "run_critic": False,
                    "rationale": "small",
                }
            )
        }
    )
    asyncio.run(
        run_multi_agent(
            client,
            skeleton,
            packs,
            ProjectType.web_app,
            artifact_dir=tmp_path,
        )
    )
    assert "critic" not in client.kinds
    assert client.kinds.count("synthesize") == 1


def test_legacy_estimate_has_no_specialist_breakdown():
    skeleton = _skeleton()
    estimate = estimate_job(skeleton, DEFAULT_MODEL, multi_agent=False)
    assert "agents" not in estimate or not estimate.get("agents")


def test_multi_agent_estimate_includes_coordinator():
    skeleton = _skeleton()
    estimate = estimate_job(skeleton, DEFAULT_MODEL, multi_agent=True)
    agents = estimate["agents"]
    assert agents["coordinator"]["calls"] == 1
    assert agents["architecture"]["calls"] == 1
    assert agents["summarization"]["calls"] == estimate["summarization_calls"]
    assert estimate["estimated_input_tokens"] > 0
