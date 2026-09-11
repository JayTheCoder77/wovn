const EDGE =
  /^\s*(?:"([^"]+)"|([A-Za-z][\w-]*))\s*-->\s*(?:"([^"]+)"|([A-Za-z][\w-]*))\s*$/;

function nodeId(label: string, ids: Map<string, string>): string {
  const key = label.trim();
  const existing = ids.get(key);
  if (existing) return existing;
  const next = `n${ids.size}`;
  ids.set(key, next);
  return next;
}

function labelText(value: string): string {
  return value.replaceAll('"', "#quot;");
}

function nodeToken(raw: string, ids: Map<string, string>): string {
  if (/^[A-Za-z][\w-]*$/.test(raw) && !raw.includes("/")) {
    return raw;
  }
  const id = nodeId(raw, ids);
  return `${id}["${labelText(raw)}"]`;
}

export function prepareMermaid(source: string): string {
  let text = source.trim();
  text = text.replace(/^```(?:mermaid)?\s*/i, "").replace(/\s*```$/i, "").trim();
  if (!text) return "";
  if (!/^(flowchart|graph|sequenceDiagram|classDiagram|erDiagram|stateDiagram)/.test(text)) {
    text = `flowchart LR\n${text}`;
  }
  const ids = new Map<string, string>();
  return text
    .split("\n")
    .map((line) => {
      const match = line.match(EDGE);
      if (!match) return line;
      const left = match[1] ?? match[2];
      const right = match[3] ?? match[4];
      if (!left || !right) return line;
      return `  ${nodeToken(left, ids)} --> ${nodeToken(right, ids)}`;
    })
    .join("\n");
}

export function stripMermaidFences(text: string): string {
  return text.replace(/```mermaid[\s\S]*?```/gi, "").trim();
}
