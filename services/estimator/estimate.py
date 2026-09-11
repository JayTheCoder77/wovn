from __future__ import annotations

from typing import Any

from skeleton_schema.models import RepoSkeleton

from estimator.pricing import estimate_cost_usd
from estimator.token_counter import count_tokens
from generation.context.packs import build_context_packs, render_global_pack, render_module_pack

PROMPT_OVERHEAD_TOKENS = 700
SUMMARY_OUTPUT_TOKENS = 550
SYNTHESIS_OUTPUT_TOKENS = 3500
SYNTHESIS_OVERHEAD_TOKENS = 900
COORDINATOR_OUTPUT_TOKENS = 400
SPECIALIST_OUTPUT_TOKENS = 800
CRITIC_OUTPUT_TOKENS = 400


def estimate_job(skeleton: RepoSkeleton, model_id: str, *, multi_agent: bool = True) -> dict[str, Any]:
    packs = build_context_packs(skeleton)
    pack_input_tokens = count_tokens(render_global_pack(packs.global_pack))
    summarization_input = 0
    for module in packs.modules:
        body_tokens = count_tokens(render_module_pack(module))
        pack_input_tokens += body_tokens
        summarization_input += body_tokens + PROMPT_OVERHEAD_TOKENS

    summarization_output = len(packs.modules) * SUMMARY_OUTPUT_TOKENS
    synthesis_input = (
        SYNTHESIS_OVERHEAD_TOKENS
        + summarization_output
        + count_tokens(render_global_pack(packs.global_pack))
    )
    synthesis_output = SYNTHESIS_OUTPUT_TOKENS

    input_tokens = summarization_input + synthesis_input
    output_tokens = summarization_output + synthesis_output
    agents: dict[str, Any] | None = None

    if multi_agent:
        global_tokens = count_tokens(render_global_pack(packs.global_pack))
        coordinator_in = PROMPT_OVERHEAD_TOKENS + min(global_tokens, 4000)
        coordinator_out = COORDINATOR_OUTPUT_TOKENS
        specialist_in = PROMPT_OVERHEAD_TOKENS + global_tokens
        specialist_out = SPECIALIST_OUTPUT_TOKENS
        critic_calls = 1 if skeleton.file_count > 20 else 0
        critic_in = (PROMPT_OVERHEAD_TOKENS + global_tokens) * critic_calls
        critic_out = CRITIC_OUTPUT_TOKENS * critic_calls
        input_tokens += coordinator_in + specialist_in * 3 + critic_in
        output_tokens += coordinator_out + specialist_out * 3 + critic_out
        agents = {
            "coordinator": {"calls": 1, "estimated_input_tokens": coordinator_in, "estimated_output_tokens": coordinator_out},
            "summarization": {
                "calls": len(packs.modules),
                "estimated_input_tokens": summarization_input,
                "estimated_output_tokens": summarization_output,
            },
            "architecture": {
                "calls": 1,
                "estimated_input_tokens": specialist_in,
                "estimated_output_tokens": specialist_out,
            },
            "surface": {
                "calls": 1,
                "estimated_input_tokens": specialist_in,
                "estimated_output_tokens": specialist_out,
            },
            "operations": {
                "calls": 1,
                "estimated_input_tokens": specialist_in,
                "estimated_output_tokens": specialist_out,
            },
            "synthesis": {
                "calls": 1,
                "estimated_input_tokens": synthesis_input,
                "estimated_output_tokens": synthesis_output,
            },
            "critic": {
                "calls": critic_calls,
                "estimated_input_tokens": critic_in,
                "estimated_output_tokens": critic_out,
            },
        }

    cost = estimate_cost_usd(model_id, input_tokens, output_tokens)
    result = {
        "model": model_id,
        "file_count": skeleton.file_count,
        "module_count": len(packs.modules),
        "summarization_calls": len(packs.modules),
        "synthesis_calls": 1,
        "pack_input_tokens": pack_input_tokens,
        "trimmed_packs": int(packs.global_pack.trimmed) + sum(1 for m in packs.modules if m.trimmed),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "languages": [lang.value for lang in skeleton.languages],
        "loc": skeleton.loc,
        "project_type": (skeleton.classifier_signals or {}).get("project_type"),
    }
    if agents is not None:
        result["agents"] = agents
    return result
