export type GroqModel = {
  id: string;
  label: string;
  input_per_million: number;
  output_per_million: number;
  default?: boolean;
};

export type Job = {
  id: string;
  repo_url: string;
  status: string;
  error: string | null;
  model: string | null;
  project_type: string | null;
  estimate: {
    model: string;
    file_count: number;
    module_count: number;
    summarization_calls: number;
    synthesis_calls: number;
    estimated_input_tokens: number;
    estimated_output_tokens: number;
    estimated_cost_usd: number;
    languages: string[];
    loc: number;
    project_type?: string | null;
  } | null;
  progress: { stage: string; message: string; tokens_used?: number } | null;
  tokens_used: number;
  created_at: string;
  updated_at: string;
  has_doc: boolean;
};

export type Settings = {
  has_groq_key: boolean;
  default_model: string;
  max_tokens: number;
};

export type GeneratedDoc = {
  project_type: string;
  title: string;
  repo_url: string;
  overview: string;
  getting_started: string;
  structure: { path: string; purpose: string }[];
  sections: {
    type: string;
    title: string;
    content: string;
    diagram?: string | null;
    items: Record<string, unknown>[];
  }[];
  search_index: { id: string; title: string; text: string }[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = await response.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean }>("/health"),
  settings: () => request<Settings>("/settings"),
  saveSettings: (payload: Partial<{ groq_api_key: string; default_model: string; max_tokens: number }>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  models: () => request<GroqModel[]>("/models"),
  jobs: () => request<Job[]>("/jobs"),
  job: (id: string) => request<Job>(`/jobs/${id}`),
  submit: (repo_url: string) => request<Job>("/jobs", { method: "POST", body: JSON.stringify({ repo_url }) }),
  confirm: (id: string, model?: string) =>
    request<Job>(`/jobs/${id}/confirm`, { method: "POST", body: JSON.stringify({ model: model || null }) }),
  doc: (id: string) => request<GeneratedDoc>(`/jobs/${id}/doc`),
};
