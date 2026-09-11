"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, LLMModel, Job, Settings } from "@/lib/api";

export default function JobPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [job, setJob] = useState<Job | null>(null);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [model, setModel] = useState("");
  const [modelInfo, setModelInfo] = useState<LLMModel | null>(null);
  const [validatingModel, setValidatingModel] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const next = await api.job(id);
        if (alive) setJob(next);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "Failed to load job");
      }
    }
    tick();
    const timer = setInterval(tick, 800);
    api.settings().then((current) => {
      setSettings(current);
      return api.models(current.llm_provider);
    }).then(setModels);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  useEffect(() => {
    if (job?.model && !model) setModel(job.model);
  }, [job, model]);

  useEffect(() => {
    if (settings && job?.llm_provider && job.llm_provider !== settings.llm_provider && model === job.model) {
      setModel(settings.default_model);
    }
  }, [job, model, settings]);

  useEffect(() => {
    if (settings?.llm_provider !== "openrouter" || !model.trim()) {
      setModelInfo(null);
      setValidatingModel(false);
      return;
    }
    setValidatingModel(true);
    const timer = setTimeout(() => {
      api.modelInfo("openrouter", model.trim())
        .then((info) => {
          setModelInfo(info);
          setError(null);
        })
        .catch((err) => {
          setModelInfo(null);
          setError(err instanceof Error ? err.message : "Could not validate model");
        })
        .finally(() => setValidatingModel(false));
    }, 350);
    return () => clearTimeout(timer);
  }, [model, settings?.llm_provider]);

  async function confirm() {
    setError(null);
    setConfirming(true);
    try {
      if (!settings) return;
      if (settings.llm_provider === "openrouter" && !modelInfo) {
        throw new Error("Enter a valid OpenRouter model before generating.");
      }
      const next = await api.confirm(id, model.trim(), settings.llm_provider);
      setJob(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setConfirming(false);
    }
  }

  if (!job) {
    return (
      <main className="shell">
        <p className="muted">{error ?? "Loading job…"}</p>
      </main>
    );
  }

  const estimate = job.estimate;
  const waiting = job.status === "awaiting_confirmation";
  const generating = ["generating", "queued_generation"].includes(job.status);

  return (
    <main className="shell">
      <p className="mono muted">{job.repo_url}</p>
      <h1>{waiting ? "Confirm generation" : job.status === "completed" ? "Docs ready" : "Working"}</h1>
      <p className="lede">{job.progress?.message ?? job.status.replaceAll("_", " ")}</p>

      {estimate ? (
        <div className="card">
          <p className="mono">
            ~{estimate.file_count} files → ~{estimate.summarization_calls} summarization calls +{" "}
            {estimate.synthesis_calls} synthesis call → est. {estimate.estimated_input_tokens.toLocaleString()} input /{" "}
            {estimate.estimated_output_tokens.toLocaleString()} output tokens → ~$
            {estimate.estimated_cost_usd.toFixed(4)} with {model || estimate.model}
          </p>
          <p className="muted">
            Detected {estimate.languages.join(", ") || "languages"} · {estimate.loc} LOC · type{" "}
            {(job.project_type || "general").replaceAll("_", " ")}
          </p>
          {waiting ? (
            <>
              <div className="row">
                <select
                  value={models.some((item) => item.id === model) ? model : ""}
                  onChange={(e) => e.target.value && setModel(e.target.value)}
                >
                  {settings?.llm_provider === "openrouter" ? <option value="">Custom model ID below</option> : null}
                  {models.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={confirm} disabled={confirming || validatingModel || (settings?.llm_provider === "openrouter" && !modelInfo) || !(settings?.llm_provider === "groq" ? settings.has_groq_key : settings?.has_openrouter_key)}>
                  {confirming ? "Starting…" : "Generate docs"}
                </button>
                <Link className="btn secondary" href="/settings">
                  {(settings?.llm_provider === "groq" ? settings.has_groq_key : settings?.has_openrouter_key) ? "Settings" : `Add ${settings?.llm_provider === "openrouter" ? "OpenRouter" : "Groq"} key`}
                </Link>
              </div>
            {settings?.llm_provider === "openrouter" ? (
              <p>
                <label>
                  Custom OpenRouter model ID
                  <br />
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="Paste a model ID, e.g. anthropic/claude-sonnet-4"
                    style={{ width: "100%", marginTop: 8 }}
                  />
                </label>
                {validatingModel ? <span className="muted"> Validating model…</span> : null}
                {modelInfo ? (
                  <span className="accent">
                    ✓ ${modelInfo.input_per_million}/M input · ${modelInfo.output_per_million}/M output
                  </span>
                ) : null}
              </p>
            ) : null}
            </>
          ) : null}
        </div>
      ) : (
        <div className="card muted">Free static pass in progress — no provider tokens used yet.</div>
      )}

      {job.status === "completed" ? (
        <p>
          <Link className="btn" href={`/docs/${job.id}`}>
            Open docs site
          </Link>
        </p>
      ) : null}
      {generating ? <p className="muted">Tokens used so far: {job.tokens_used.toLocaleString()}</p> : null}
      {job.error ? <p className="error">{job.error}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}
