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

  async function confirm() {
    setError(null);
    setConfirming(true);
    try {
      if (!settings) return;
      const next = await api.confirm(id, model, settings.llm_provider);
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
            <div className="row">
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
              <button type="button" onClick={confirm} disabled={confirming || !(settings?.llm_provider === "groq" ? settings.has_groq_key : settings?.has_openrouter_key)}>
                {confirming ? "Starting…" : "Generate docs"}
              </button>
              <Link className="btn secondary" href="/settings">
                {(settings?.llm_provider === "groq" ? settings.has_groq_key : settings?.has_openrouter_key) ? "Settings" : `Add ${settings?.llm_provider === "openrouter" ? "OpenRouter" : "Groq"} key`}
              </Link>
            </div>
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
