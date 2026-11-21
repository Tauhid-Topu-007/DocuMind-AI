import { useState } from "react";
import { ChevronDown, FileText, Globe } from "lucide-react";
import { useApp } from "../../context/AppContext.jsx";

export default function SourcePicker() {
  const { readySources, selectedIds, setSelectedIds, activeIds } = useApp();
  const [open, setOpen] = useState(false);
  const toggle = (id) => setSelectedIds((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const label = activeIds.length ? `${activeIds.length} selected` : `All sources (${readySources.length})`;
  return (
    <div className="relative">
      <button className="btn btn-ghost !py-1.5" onClick={() => setOpen((o) => !o)}>
        {label} <ChevronDown size={14} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-20 mt-2 max-h-72 w-72 overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-2 shadow-xl">
            {readySources.length === 0 && <p className="p-2 text-sm text-slate-500">No processed sources yet.</p>}
            {readySources.map((s) => (
              <label key={s.id} className="flex cursor-pointer items-center gap-2 rounded-lg p-2 text-sm hover:bg-slate-800">
                <input type="checkbox" checked={selectedIds.includes(s.id)} onChange={() => toggle(s.id)} />
                {s.type === "pdf" ? <FileText size={14} /> : <Globe size={14} />}
                <span className="truncate">{s.name}</span>
              </label>
            ))}
            {selectedIds.length > 0 && (
              <button className="mt-1 w-full rounded-lg p-2 text-left text-xs text-indigo-300 hover:bg-slate-800" onClick={() => setSelectedIds([])}>
                Clear selection (search all)
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
