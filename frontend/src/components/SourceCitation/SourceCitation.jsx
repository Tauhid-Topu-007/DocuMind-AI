import { useState } from "react";
import { FileText, Globe } from "lucide-react";

export default function SourceCitation({ sources }) {
  const [open, setOpen] = useState(null);
  if (!sources?.length) return null;
  return (
    <div className="mt-3 border-t border-slate-800 pt-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</div>
      <div className="flex flex-wrap gap-2">
        {sources.map((s) => {
          const isPdf = s.source_type === "pdf";
          const label = isPdf ? `${s.filename}${s.page_number ? ` · p.${s.page_number}` : ""}` : s.title || s.url;
          return (
            <button
              key={s.index}
              onClick={() => setOpen(open === s.index ? null : s.index)}
              className={`flex max-w-full items-center gap-1.5 rounded-lg border px-2 py-1 text-xs transition ${open === s.index ? "border-indigo-400 bg-indigo-500/10" : "border-slate-700 hover:bg-slate-800"}`}
            >
              <span className="font-semibold text-indigo-300">[{s.index}]</span>
              {isPdf ? <FileText size={12} /> : <Globe size={12} />}
              <span className="truncate">{label}</span>
            </button>
          );
        })}
      </div>
      {open && (() => {
        const s = sources.find((x) => x.index === open);
        return (
          <div className="mt-2 rounded-xl bg-slate-950/70 p-3 text-xs text-slate-400">
            {s.url && <a href={s.url} target="_blank" rel="noreferrer noopener" className="mb-1 block truncate text-indigo-300 underline">{s.url}</a>}
            <p className="whitespace-pre-wrap">{s.snippet}{s.snippet?.length >= 300 ? "…" : ""}</p>
            {typeof s.score === "number" && <p className="mt-1 text-slate-600">relevance {s.score.toFixed(2)}</p>}
          </div>
        );
      })()}
    </div>
  );
}
