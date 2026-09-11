export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type GroqModel = {
  id: string;
  label: string;
  input_per_million: number;
  output_per_million: number;
  default?: boolean;
};

export type Job = {
  id: string;
  user_id: string;
  repo_id: string;
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

export type AuthUser = {
  id: string;
  github_id: number;
  email: string | null;
  display_name: string;
};

export type Repo = {
  id: string;
  user_id: string;
  provider: string;
  full_name: string;
  default_url: string;
  default_branch: string | null;
  visibility: string;
  last_analyzed_at: string | null;
};

export type GithubRepoOption = {
  full_name: string;
  html_url: string;
  visibility: string;
  default_branch: string | null;
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

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function redirectIfProtected(path: string) {
  if (typeof window === "undefined") return;
  if (path.startsWith("/auth/")) return;
  const current = window.location.pathname;
  if (current.startsWith("/settings") || current.startsWith("/jobs") || current.startsWith("/docs")) {
    window.location.href = "/";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (response.status === 401) {
    redirectIfProtected(path);
    throw new ApiError(401, "Sign in required");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean }>("/health"),
  me: () => request<AuthUser>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  settings: () => request<Settings>("/settings"),
  saveSettings: (payload: Partial<{ groq_api_key: string; default_model: string; max_tokens: number }>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  models: () => request<GroqModel[]>("/models"),
  repos: () => request<Repo[]>("/repos"),
  addRepo: (url: string) => request<Repo>("/repos", { method: "POST", body: JSON.stringify({ url }) }),
  githubRepos: () => request<GithubRepoOption[]>("/github/repos"),
  createRepoJob: (repoId: string) => request<Job>(`/repos/${repoId}/jobs`, { method: "POST" }),
  jobs: () => request<Job[]>("/jobs"),
  job: (id: string) => request<Job>(`/jobs/${id}`),
  submit: (repo_url: string) => request<Job>("/jobs", { method: "POST", body: JSON.stringify({ repo_url }) }),
  confirm: (id: string, model?: string) =>
    request<Job>(`/jobs/${id}/confirm`, { method: "POST", body: JSON.stringify({ model: model || null }) }),
  doc: (id: string) => request<GeneratedDoc>(`/jobs/${id}/doc`),
};

export function githubLoginUrl() {
  return `${API_BASE}/auth/github/login`;
}
