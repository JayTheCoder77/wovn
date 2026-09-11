from __future__ import annotations

from typing import Any

from skeleton_schema.models import RepoSkeleton

from estimator.pricing import estimate_cost_usd
from estimator.token_counter import count_tokens
from generation.modules import file_context, group_files

PROMPT_OVERHEAD_TOKENS = 700
SUMMARY_OUTPUT_TOKENS = 550
SYNTHESIS_OUTPUT_TOKENS = 3500
SYNTHESIS_OVERHEAD_TOKENS = 900


def estimate_job(skeleton: RepoSkeleton, model_id: str) -> dict[str, Any]:
    groups = group_files(skeleton.files)
    summarization_input = 0
    for group in groups:
        body = "\n".join(file_context(f) for f in group.files)
        summarization_input += count_tokens(body) + PROMPT_OVERHEAD_TOKENS

    summarization_output = len(groups) * SUMMARY_OUTPUT_TOKENS
    synthesis_input = (
        SYNTHESIS_OVERHEAD_TOKENS
        + (len(groups) * SUMMARY_OUTPUT_TOKENS)
        + count_tokens("\n".join(skeleton.tree[:200]))
    )
    synthesis_output = SYNTHESIS_OUTPUT_TOKENS

    input_tokens = summarization_input + synthesis_input
    output_tokens = summarization_output + synthesis_output
    cost = estimate_cost_usd(model_id, input_tokens, output_tokens)
    return {
        "model": model_id,
        "file_count": skeleton.file_count,
        "module_count": len(groups),
        "summarization_calls": len(groups),
        "synthesis_calls": 1,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "languages": [lang.value for lang in skeleton.languages],
        "loc": skeleton.loc,
        "project_type": (skeleton.classifier_signals or {}).get("project_type"),
    }
