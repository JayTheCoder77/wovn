"use client";

import { useEffect, useId, useState } from "react";
import { prepareMermaid } from "@/lib/mermaid";

let mermaidInit: Promise<typeof import("mermaid").default> | null = null;

function loadMermaid() {
  if (!mermaidInit) {
    mermaidInit = import("mermaid").then((mod) => {
      mod.default.initialize({
        startOnLoad: false,
        theme: "dark",
        securityLevel: "strict",
        suppressErrorRendering: true,
      });
      return mod.default;
    });
  }
  return mermaidInit;
}

function isErrorSvg(svg: string): boolean {
  return svg.includes("Syntax error") || svg.includes("error-icon");
}

export default function Mermaid({ chart }: { chart: string }) {
  const reactId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const prepared = prepareMermaid(chart);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    setSvg(null);
    if (!prepared) {
      setFailed(true);
      return;
    }
    (async () => {
      try {
        const mermaid = await loadMermaid();
        const { svg: rendered } = await mermaid.render(`mmd${reactId}`, prepared);
        if (cancelled) return;
        if (isErrorSvg(rendered)) {
          setFailed(true);
          return;
        }
        setSvg(rendered);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [prepared, reactId]);

  if (failed) {
    return <pre className="diagram">{prepared || chart}</pre>;
  }
  if (!svg) {
    return <p className="muted">Rendering diagram…</p>;
  }
  return <div className="diagram mermaid-wrap" dangerouslySetInnerHTML={{ __html: svg }} />;
}
