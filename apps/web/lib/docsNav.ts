export function sectionAnchor(id: string): string {
  if (id === "overview" || id === "getting-started" || id === "structure") {
    return id;
  }
  if (id.startsWith("structure-") || id.startsWith("structure/")) {
    return "structure";
  }
  const section = /^section-(\d+)/.exec(id);
  if (section) {
    return `section-${section[1]}`;
  }
  return id;
}

export function scrollToSection(id: string): void {
  const anchor = sectionAnchor(id);
  const el = document.getElementById(anchor);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  history.replaceState(null, "", `#${anchor}`);
}
