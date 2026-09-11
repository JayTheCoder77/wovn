"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, Job } from "@/lib/api";

export default function HomePage() {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    api.jobs().then(setJobs).catch(() => undefined);
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

  return (
    <main className="shell">
      <p className="mono muted">Static analysis · BYOK Groq · one-time snapshot</p>
      <h1>Weave docs from a repo, fast.</h1>
      <p className="lede">
        Paste a public GitHub URL. Wovn clones it in isolation, builds a tree-sitter skeleton, estimates Groq
        cost against your key, then generates a structured docs site.
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
      {error ? <p className="error">{error}</p> : null}

      {jobs.length ? (
        <section className="job-list">
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
