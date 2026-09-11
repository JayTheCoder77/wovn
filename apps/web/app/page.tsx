"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, AuthUser, GithubRepoOption, Job, Repo, githubLoginUrl } from "@/lib/api";

function formatWhen(iso: string | null | undefined) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function repoName(url: string) {
  return url.replace("https://github.com/", "").replace(/\.git$/, "");
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default function HomePage() {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [githubRepos, setGithubRepos] = useState<GithubRepoOption[]>([]);
  const [picked, setPicked] = useState("");

  useEffect(() => {
    api
      .me()
      .then((current) => {
        setUser(current);
        return Promise.all([api.jobs(), api.repos(), api.githubRepos().catch(() => [])]);
      })
      .then(([jobRows, repoRows, ghRows]) => {
        setJobs(jobRows);
        setRepos(repoRows);
        setGithubRepos(ghRows);
      })
      .catch(() => setUser(null));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const job = await api.submit(url.trim());
      window.location.href = `/jobs/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start job");
      setPending(false);
    }
  }

  async function analyzeRepo(repoId: string) {
    setError(null);
    setPending(true);
    try {
      const job = await api.createRepoJob(repoId);
      window.location.href = `/jobs/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start job");
      setPending(false);
    }
  }

  async function addPicked() {
    if (!picked) return;
    setError(null);
    setPending(true);
    try {
      const repo = await api.addRepo(picked);
      const job = await api.createRepoJob(repo.id);
      window.location.href = `/jobs/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add repository");
      setPending(false);
    }
  }

  if (user === undefined) {
    return (
      <main className="landing">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="landing">
        <section className="hero">
          <p className="kicker">Static analysis · BYOK Groq · private repos</p>
          <h1>Turn a GitHub repo into a docs site.</h1>
          <p className="lede">
            Wovn clones the repository in isolation, reads structure with tree-sitter, estimates cost on your Groq
            key, then writes overview, getting started, and architecture — without executing the code.
          </p>
          <p className="row">
            <a className="btn" href={githubLoginUrl()}>
              Sign in with GitHub
            </a>
          </p>
        </section>
        <section className="step-grid">
          <article className="step-card">
            <p className="mono accent">01</p>
            <h3>Analyze</h3>
            <p>Shallow clone with hooks disabled. Python, TypeScript, JavaScript, Go, and Rust become a skeleton plus ContextPacks.</p>
          </article>
          <article className="step-card">
            <p className="mono accent">02</p>
            <h3>Estimate</h3>
            <p>See token counts and dollar cost before any Groq call. Confirm only when the budget looks right.</p>
          </article>
          <article className="step-card">
            <p className="mono accent">03</p>
            <h3>Generate</h3>
            <p>Coordinator and specialist agents draft architecture, API surface, and operations, then merge into a searchable docs site.</p>
          </article>
        </section>
      </main>
    );
  }

  return (
    <main className="landing">
      <section className="hero hero-compact">
        <p className="kicker">Signed in as {user.display_name}</p>
        <h1>Generate docs from a repo.</h1>
        <p className="lede">
          Paste a GitHub URL or pick from your account. Wovn analyzes it statically, shows a cost estimate, then
          writes the docs site with your Groq key.
        </p>
      </section>

      <section className="generate-panel">
        <form className="row" onSubmit={onSubmit}>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            aria-label="GitHub repository URL"
          />
          <button type="submit" disabled={pending}>
            {pending ? "Starting…" : "Analyze URL"}
          </button>
        </form>
        {githubRepos.length ? (
          <div className="row">
            <select value={picked} onChange={(e) => setPicked(e.target.value)} aria-label="Your GitHub repositories">
              <option value="">Pick from GitHub…</option>
              {githubRepos.map((repo) => (
                <option key={repo.full_name} value={repo.html_url}>
                  {repo.full_name} ({repo.visibility})
                </option>
              ))}
            </select>
            <button type="button" className="secondary" onClick={addPicked} disabled={pending || !picked}>
              Analyze selected
            </button>
          </div>
        ) : (
          <p className="muted">GitHub repos will appear here after sign-in if the API can list them.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
      </section>

      <div className="home-split">
        <section>
          <div className="section-head">
            <h2>Repositories</h2>
            <p className="muted">{repos.length ? `${repos.length} registered` : "None yet"}</p>
          </div>
          {repos.length ? (
            <div className="repo-grid">
              {repos.map((repo) => (
                <article key={repo.id} className="repo-card">
                  <p className="mono">{repo.full_name}</p>
                  <p className="muted">
                    {repo.visibility}
                    {formatWhen(repo.last_analyzed_at) ? ` · ${formatWhen(repo.last_analyzed_at)}` : " · not analyzed yet"}
                  </p>
                  <button type="button" className="secondary" onClick={() => analyzeRepo(repo.id)} disabled={pending}>
                    Run analysis
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-hint">Register a repo above to keep it here for later runs.</p>
          )}
        </section>

        <section>
          <div className="section-head">
            <h2>Recent jobs</h2>
            <p className="muted">{jobs.length ? `${jobs.length} shown` : "None yet"}</p>
          </div>
          {jobs.length ? (
            <div className="job-list">
              {jobs.map((job) => (
                <Link key={job.id} href={job.has_doc ? `/docs/${job.id}` : `/jobs/${job.id}`}>
                  <span>
                    <span className="mono">{repoName(job.repo_url)}</span>
                    <span className="muted job-meta">{formatWhen(job.updated_at) ?? ""}</span>
                  </span>
                  <span className={`status status-${job.status}`}>{statusLabel(job.status)}</span>
                </Link>
              ))}
            </div>
          ) : (
            <p className="empty-hint">Jobs show up after you start an analysis.</p>
          )}
        </section>
      </div>
    </main>
  );
}
