"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, LLMModel, LLMProvider, Settings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [provider, setProvider] = useState<LLMProvider>("groq");
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [cap, setCap] = useState(200000);
  const [modelInfo, setModelInfo] = useState<LLMModel | null>(null);
  const [validatingModel, setValidatingModel] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.settings()
      .then(async (s) => {
        setSettings(s);
        setProvider(s.llm_provider);
        const m = await api.models(s.llm_provider);
        setModels(m);
        setModel(s.default_model);
        setCap(s.max_tokens);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load settings"));
  }, []);

  useEffect(() => {
    if (provider !== "openrouter" || !model.trim()) {
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
  }, [model, provider]);

  async function changeProvider(next: LLMProvider) {
    setProvider(next);
    setKey("");
    setError(null);
    try {
      const [nextSettings, nextModels] = await Promise.all([
        api.saveSettings({ llm_provider: next }),
        api.models(next),
      ]);
      setSettings(nextSettings);
      setModels(nextModels);
      setModel(nextSettings.default_model);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change provider");
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const payload: { llm_provider: LLMProvider; default_model: string; max_tokens: number; groq_api_key?: string; openrouter_api_key?: string } = {
        llm_provider: provider,
        default_model: model,
        max_tokens: cap,
      };
      if (provider === "openrouter" && !modelInfo) {
        throw new Error("Enter a valid OpenRouter model before saving.");
      }
      if (key.trim()) {
        if (provider === "groq") payload.groq_api_key = key.trim();
        else payload.openrouter_api_key = key.trim();
      }
      const next = await api.saveSettings(payload);
      setSettings(next);
      setKey("");
      setMessage("Saved. Per-run model overrides reset to this default on the next job.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <main className="shell">
      <h1>Settings</h1>
      <p className="lede">
        Your provider keys are encrypted at rest (key id fernet-v1) and used only for confirmed generation jobs. Rotating{" "}
        <span className="mono">WOVN_SECRET_KEY</span> invalidates stored provider and GitHub secrets.
      </p>
      <form className="card" onSubmit={onSubmit}>
        <p className="muted">
          Key status: {(provider === "groq" ? settings?.has_groq_key : settings?.has_openrouter_key) ? "saved" : "not set"}
        </p>
        <p>
          <label>
            Provider
            <br />
            <select value={provider} onChange={(e) => changeProvider(e.target.value as LLMProvider)} style={{ marginTop: 8, width: "100%" }}>
              <option value="groq">Groq</option>
              <option value="openrouter">OpenRouter</option>
            </select>
          </label>
        </p>
        <p>
          <label>
            {provider === "groq" ? "Groq" : "OpenRouter"} API key
            <br />
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={(provider === "groq" ? settings?.has_groq_key : settings?.has_openrouter_key) ? "•••••••• (leave blank to keep)" : provider === "groq" ? "gsk_…" : "sk-or-…"}
              style={{ width: "100%", marginTop: 8 }}
            />
          </label>
        </p>
        <p>
          <label>
            {provider === "openrouter" ? "Recommended default models" : "Default model"}
            <br />
            <select
              value={models.some((item) => item.id === model) ? model : ""}
              onChange={(e) => e.target.value && setModel(e.target.value)}
              style={{ marginTop: 8, width: "100%" }}
            >
              {provider === "openrouter" ? <option value="">Custom model ID below</option> : null}
              {models.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label} — ${item.input_per_million}/M in · ${item.output_per_million}/M out
                </option>
              ))}
            </select>
          </label>
        </p>
        {provider === "openrouter" ? (
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
        <p>
          <label>
            Hard token cap per run
            <br />
            <input
              type="number"
              min={1000}
              value={cap}
              onChange={(e) => setCap(Number(e.target.value))}
              style={{ width: "100%", marginTop: 8 }}
            />
          </label>
        </p>
        <button type="submit" disabled={provider === "openrouter" && (validatingModel || !modelInfo)}>Save</button>
        {message ? <p className="muted">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </form>
    </main>
  );
}
