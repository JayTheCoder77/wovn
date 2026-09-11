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
            Default model
            <br />
            <select value={model} onChange={(e) => setModel(e.target.value)} style={{ marginTop: 8, width: "100%" }}>
              {models.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label} — ${item.input_per_million}/M in · ${item.output_per_million}/M out
                </option>
              ))}
            </select>
          </label>
        </p>
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
        <button type="submit">Save</button>
        {message ? <p className="muted">{message}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </form>
    </main>
  );
}
