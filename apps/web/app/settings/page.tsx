"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, GroqModel, Settings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [models, setModels] = useState<GroqModel[]>([]);
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [cap, setCap] = useState(200000);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.settings(), api.models()]).then(([s, m]) => {
      setSettings(s);
      setModels(m);
      setModel(s.default_model);
      setCap(s.max_tokens);
    });
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const payload: { default_model: string; max_tokens: number; groq_api_key?: string } = {
        default_model: model,
        max_tokens: cap,
      };
      if (key.trim()) payload.groq_api_key = key.trim();
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
      <p className="lede">Your Groq key is encrypted at rest and used only for confirmed generation jobs.</p>
      <form className="card" onSubmit={onSubmit}>
        <p className="muted">
          Key status: {settings?.has_groq_key ? "saved" : "not set"}
        </p>
        <p>
          <label>
            Groq API key
            <br />
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={settings?.has_groq_key ? "•••••••• (leave blank to keep)" : "gsk_…"}
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
