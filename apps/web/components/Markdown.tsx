"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Mermaid from "./Mermaid";

export default function Markdown({ children }: { children: string }) {
  const text = children?.trim() ?? "";
  if (!text) return null;
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children: codeChildren }) {
            const value = String(codeChildren).replace(/\n$/, "");
            const lang = /language-(\w+)/.exec(className || "")?.[1];
            const fenced = Boolean(className) || value.includes("\n");
            if (fenced && lang === "mermaid") {
              return <Mermaid chart={value} />;
            }
            if (fenced) {
              return (
                <pre>
                  <code className={className}>{value}</code>
                </pre>
              );
            }
            return <code>{value}</code>;
          },
          a({ href, children: linkChildren }) {
            const external = href?.startsWith("http");
            return (
              <a href={href} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined}>
                {linkChildren}
              </a>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

export function stripLeadingHeading(text: string, title: string) {
  const escaped = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+");
  return text
    .replace(new RegExp(`^#{1,3}\\s*${escaped}\\s*\\n+`, "i"), "")
    .replace(new RegExp(`^${escaped}\\s*\\n+`, "i"), "");
}

function cell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.path === "string") {
      const line = record.line != null ? `:${record.line}` : "";
      return `${record.path}${line}`;
    }
    return JSON.stringify(value);
  }
  return String(value);
}

export function ItemTable({ items }: { items: Record<string, unknown>[] }) {
  if (!items.length) return null;
  const keys = Array.from(new Set(items.flatMap((item) => Object.keys(item))));
  if (!keys.length) return null;
  return (
    <div className="md">
      <table>
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key}>{key.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={index}>
              {keys.map((key) => (
                <td key={key}>{cell(item[key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
