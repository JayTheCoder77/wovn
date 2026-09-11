# Cost Model & BYOK UX

## Principle
Since inference runs on the user's own Groq API key, cost transparency and predictability are core to trust in the product — a bad estimate spends the user's money, not the platform's.

## Flow

### 1. Free static pass (no LLM calls, no cost)
- Clone + tree-sitter analysis happens entirely locally
- Produces exact file counts, LOC, and skeleton token size — all known before any model is chosen or called

### 2. Estimate & confirm gate
- Using skeleton size, estimate:
  - Number of summarization calls (proportional to module/file count)
  - Total input + output token volume
- Price the estimate against the user's **default model preference** (Groq pricing table, per-model)
- Display something like:
  > "~48 files → ~6 summarization calls + 1 synthesis call → est. 42k input / 8k output tokens → ~$0.03 with [default model]"
- Require explicit user confirmation before spending any tokens
- Provide a "change model" control at this step to override the default for this run

### 3. Live progress during generation
- Since Groq is fast, stream progress updates (e.g., "Analyzing module 4/12 — 18k tokens used so far")
- Reinforces both the speed positioning and real-time cost transparency

### 4. Safety caps
- Configurable hard max-token ceiling per run (default set conservatively, user-adjustable)
- Protects against edge cases (e.g., unexpectedly large monorepo) silently draining the user's Groq balance

## Model selection UX
- User sets a **default model preference** once (stored with account/settings)
- Each run auto-applies the default to the estimate
- Override available per run via a lightweight control next to the estimate
- **Decision needed:** does an override persist as the new default for future runs, or reset to the saved default next time? (Current lean: reset to saved default each new run, to keep behavior predictable.)

## Groq pricing integration
- Maintain a pricing table for available Groq models (input/output cost per token), refreshed periodically from Groq's published pricing
- Estimation math: `estimated_cost = (input_tokens * input_price) + (output_tokens * output_price)`
