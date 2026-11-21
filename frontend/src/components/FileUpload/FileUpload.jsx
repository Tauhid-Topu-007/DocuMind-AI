import { useRef, useState } from "react";
import { CheckCircle2, Loader2, UploadCloud, XCircle } from "lucide-react";
import { errMsg, uploadDocument } from "../../services/api";
import { useApp } from "../../context/AppContext.jsx";

const MAX_MB = 20; // keep in sync with MAX_UPLOAD_SIZE_MB on the backend

export default function FileUpload() {
  const { refreshSources } = useApp();
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [items, setItems] = useState([]);

  const handle = async (fileList) => {
    const files = Array.from(fileList);
    if (!files.length) return;
    const base = Date.now();
    setItems((p) => [...files.map((f, i) => ({ key: base + i, name: f.name, state: "uploading" })), ...p].slice(0, 6));
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const key = base + i;
      const set = (state, error) => setItems((p) => p.map((x) => (x.key === key ? { ...x, state, error } : x)));
      if (!f.name.toLowerCase().endsWith(".pdf")) { set("error", "Only PDF files are supported"); continue; }
      if (f.size > MAX_MB * 1024 * 1024) { set("error", `Larger than ${MAX_MB} MB`); continue; }
      try {
        await uploadDocument(f);
        set("done");
        refreshSources();
      } catch (e) {
        set("error", errMsg(e));
      }
    }
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-4 py-8 text-center transition ${drag ? "border-indigo-400 bg-indigo-500/10" : "border-slate-700 hover:border-slate-500"}`}
      >
        <UploadCloud className="text-indigo-400" size={28} />
        <p className="text-sm font-medium">Drop PDFs here or click to browse</p>
        <p className="text-xs text-slate-500">Multiple files supported · up to {MAX_MB} MB each</p>
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => handle(e.target.files)} />
      </div>
      {items.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-sm">
          {items.map((it) => (
            <li key={it.key} className="flex items-center gap-2">
              {it.state === "uploading" && <Loader2 size={16} className="animate-spin text-indigo-300" />}
              {it.state === "done" && <CheckCircle2 size={16} className="text-emerald-400" />}
              {it.state === "error" && <XCircle size={16} className="text-red-400" />}
              <span className="truncate">{it.name}</span>
              {it.error && <span className="truncate text-xs text-red-300">— {it.error}</span>}
              {it.state === "done" && <span className="text-xs text-slate-500">uploaded, indexing…</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
