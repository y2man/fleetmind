import type { ReactNode } from "react";

const inline = (text: string): ReactNode[] =>
  text.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.length > 4 && p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p));

/** Renders the plain-text answers the assistant writes: paragraphs, "- " bullets and **bold**. Everything is escaped by React. */
export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];
  const flush = () => {
    if (bullets.length) blocks.push(<ul key={`u${blocks.length}`} className="list-disc space-y-1 pl-5">{bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}</ul>);
    bullets = [];
  };
  text.split("\n").forEach((line) => {
    const m = /^\s*[-•*]\s+(.*)$/.exec(line);
    if (m) bullets.push(m[1]);
    else {
      flush();
      if (line.trim()) blocks.push(<p key={`p${blocks.length}`}>{inline(line.replace(/^#+\s*/, ""))}</p>);
    }
  });
  flush();
  return <div className="space-y-2 text-sm leading-relaxed">{blocks}</div>;
}
