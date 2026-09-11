"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, GeneratedDoc } from "@/lib/api";

function renderMarkdown(text: string) {
  const blocks = text.trim().split(/\n{2,}/);
  return blocks.map((block, index) => {
    if (block.startsWith("```")) {
      const inner = block.replace(/^```[a-zA-Z]*\n?/, "").replace(/```$/, "");
      return (
        <pre key={index}>
          <code>{inner}</code>
        </pre>
      );
    }
    if (block.startsWith("# ")) return <h2 key={index}>{block.slice(2)}</h2>;
    if (block.startsWith("## ")) return <h3 key={index}>{block.slice(3)}</h3>;
    if (block.startsWith("- ")) {
      return (
        <ul key={index}>
          {block.split("\n").map((line, i) => (
            <li key={i}>{line.replace(/^- /, "")}</li>
          ))}
        </ul>
      );
    }
    return <p key={index}>{block}</p>;
  });
}

export default function DocsPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [doc, setDoc] = useState<GeneratedDoc | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState("overview");

  useEffect(() => {
    api
      .doc(id)
      .then(setDoc)
      .catch((err) => setError(err instanceof Error ? err.message : "Doc load failed"));
  }, [id]);

  const nav = useMemo(() => {
    if (!doc) return [];
    return [
      { id: "overview", title: "Overview" },
      { id: "getting-started", title: "Getting started" },
      { id: "structure", title: "Project structure" },
      ...doc.sections.map((section, index) => ({
        id: `section-${index}`,
        title: section.title,
      })),
    ];
  }, [doc]);

  const hits = useMemo(() => {
    if (!doc || !query.trim()) return [];
    const needle = query.trim().toLowerCase();
    return doc.search_index.filter(
      (entry) =>
        entry.title.toLowerCase().includes(needle) || entry.text.toLowerCase().includes(needle),
    );
  }, [doc, query]);

  if (error) {
    return (
      <main className="shell">
        <p className="error">{error}</p>
      </main>
    );
  }
  if (!doc) {
    return (
      <main className="shell">
        <p className="muted">Loading documentation…</p>
      </main>
    );
  }

  return (
    <div className="docs">
      <aside className="sidebar">
        <p className="brand" style={{ fontSize: 22, margin: "0 0 12px" }}>
          {doc.title}
        </p>
        <p className="mono muted">{doc.project_type.replaceAll("_", " ")}</p>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search docs" />
        {query && hits.length === 0 ? <p className="muted">No matches</p> : null}
        {(query ? hits.map((h) => ({ id: h.id, title: h.title })) : nav).map((item) => (
          <a
            key={item.id}
            href={`#${item.id.startsWith("section-") || ["overview", "getting-started", "structure"].includes(item.id) ? item.id.replace(/structure-.*/, "structure") : item.id}`}
            className={active === item.id ? "active" : ""}
            onClick={() => setActive(item.id)}
          >
            {item.title}
          </a>
        ))}
      </aside>
      <article className="article">
        <section id="overview">
          <h2>Overview</h2>
          {renderMarkdown(doc.overview)}
        </section>
        <section id="getting-started">
          <h2>Getting started</h2>
          {renderMarkdown(doc.getting_started)}
        </section>
        <section id="structure">
          <h2>Project structure</h2>
          <ul>
            {doc.structure.map((item) => (
              <li key={item.path}>
                <span className="mono">{item.path}</span> — {item.purpose}
              </li>
            ))}
          </ul>
        </section>
        {doc.sections.map((section, index) => (
          <section id={`section-${index}`} key={`${section.type}-${index}`}>
            <h2>{section.title}</h2>
            {section.diagram ? <pre className="diagram">{section.diagram}</pre> : null}
            {renderMarkdown(section.content)}
            {section.items?.length ? (
              <ul>
                {section.items.map((item, i) => (
                  <li key={i} className="mono">
                    {JSON.stringify(item)}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </article>
    </div>
  );
}
