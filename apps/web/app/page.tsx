"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, AuthUser, GithubRepoOption, Job, Repo, githubLoginUrl } from "@/lib/api";

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
      <main className="shell">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="shell">
        <p className="mono muted">Static analysis · BYOK Groq · signed-in repos</p>
        <h1>Weave docs from a repo, fast.</h1>
        <p className="lede">
          Sign in with GitHub to register repositories — including private ones you can access — then generate docs
          with your Groq key.
        </p>
        <p className="row">
          <a className="btn" href={githubLoginUrl()}>
            Sign in with GitHub
          </a>
        </p>
      </main>
    );
  }

  return (
    <main className="shell">
      <p className="mono muted">Static analysis · BYOK Groq · one-time snapshot</p>
      <h1>Weave docs from a repo, fast.</h1>
      <p className="lede">
        Add a GitHub URL or pick a repository from your account. Wovn clones it in isolation, builds a tree-sitter
        skeleton, estimates Groq cost against your key, then generates a structured docs site.
      </p>
      <form className="row" onSubmit={onSubmit}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          aria-label="GitHub repository URL"
        />
        <button type="submit" disabled={pending}>
          {pending ? "Starting…" : "Analyze"}
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
      ) : null}
      {error ? <p className="error">{error}</p> : null}

      {repos.length ? (
        <section className="job-list">
          <h2>Your repositories</h2>
          {repos.map((repo) => (
            <div key={repo.id} className="card" style={{ marginTop: 10 }}>
              <p className="mono">{repo.full_name}</p>
              <p className="muted">
                {repo.visibility}
                {repo.last_analyzed_at ? ` · last analyzed ${repo.last_analyzed_at}` : ""}
              </p>
              <button type="button" onClick={() => analyzeRepo(repo.id)} disabled={pending}>
                Run analysis
              </button>
            </div>
          ))}
        </section>
      ) : null}

      {jobs.length ? (
        <section className="job-list">
          <h2>Job history</h2>
          {jobs.map((job) => (
            <Link key={job.id} href={job.has_doc ? `/docs/${job.id}` : `/jobs/${job.id}`}>
              <span className="mono">{job.repo_url.replace("https://github.com/", "")}</span>
              <span className="muted">{job.status.replaceAll("_", " ")}</span>
            </Link>
          ))}
        </section>
      ) : null}
    </main>
  );
}
