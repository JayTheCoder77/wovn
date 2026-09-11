"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Markdown, { ItemTable, stripLeadingHeading } from "@/components/Markdown";
import Mermaid from "@/components/Mermaid";
import { api, GeneratedDoc } from "@/lib/api";
import { sectionAnchor, scrollToSection } from "@/lib/docsNav";
import { stripMermaidFences } from "@/lib/mermaid";

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
        {(query ? hits.map((h) => ({ id: h.id, title: h.title })) : nav).map((item) => {
          const anchor = sectionAnchor(item.id);
          return (
            <a
              key={`${item.id}-${item.title}`}
              href={`#${anchor}`}
              className={active === anchor ? "active" : ""}
              onClick={(event) => {
                event.preventDefault();
                setActive(anchor);
                scrollToSection(item.id);
              }}
            >
              {item.title}
            </a>
          );
        })}
      </aside>
      <article className="article">
        <section id="overview">
          <h2>Overview</h2>
          <Markdown>{stripLeadingHeading(doc.overview, "Overview")}</Markdown>
        </section>
        <section id="getting-started">
          <h2>Getting started</h2>
          <Markdown>{stripLeadingHeading(doc.getting_started, "Getting started")}</Markdown>
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
            {section.diagram ? <Mermaid chart={section.diagram} /> : null}
            <Markdown>
              {stripLeadingHeading(
                section.diagram ? stripMermaidFences(section.content) : section.content,
                section.title,
              )}
            </Markdown>
            {section.items?.length ? <ItemTable items={section.items} /> : null}
          </section>
        ))}
      </article>
    </div>
  );
}
