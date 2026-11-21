import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FileText, Globe, Loader2, MessageSquare, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import FileUpload from "../components/FileUpload/FileUpload.jsx";
import WebsiteInput from "../components/WebsiteInput/WebsiteInput.jsx";
import { useApp } from "../context/AppContext.jsx";
import * as api from "../services/api";

const badge = {
  processed: "bg-emerald-500/15 text-emerald-300",
  processing: "bg-amber-500/15 text-amber-300",
  failed: "bg-red-500/15 text-red-300",
};

function Row({ icon: Icon, title, subtitle, item, onAsk, onSummarize, onDelete, onReprocess }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
      <Icon size={20} className="shrink-0 text-indigo-300" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{title}</div>
        <div className="truncate text-xs text-slate-500">{subtitle}</div>
        {item.error && <div className="mt-1 text-xs text-red-300">{item.error}</div>}
      </div>
      <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${badge[item.status] || ""}`}>
        {item.status === "processing" && <Loader2 size={12} className="animate-spin" />}{item.status}
      </span>
      <div className="flex gap-1">
        {item.status === "processed" && (
          <>
            <button className="btn btn-ghost !px-2 !py-1" title="Ask" onClick={onAsk}><MessageSquare size={14} /></button>
            <button className="btn btn-ghost !px-2 !py-1" title="Summarize" onClick={onSummarize}><Sparkles size={14} /></button>
          </>
        )}
        {onReprocess && item.status !== "processing" && (
          <button className="btn btn-ghost !px-2 !py-1" title="Reprocess" onClick={onReprocess}><RefreshCw size={14} /></button>
        )}
        <button className="btn btn-ghost !px-2 !py-1 hover:!text-red-300" title="Delete" onClick={onDelete}><Trash2 size={14} /></button>
      </div>
    </div>
  );
}

export default function Documents() {
  const { documents, websites, refreshSources } = useApp();
  const navigate = useNavigate();
  const go = (id, autoPrompt) => navigate("/chat", { state: { fresh: Date.now(), sourceIds: [id], autoPrompt } });
  const run = (fn) => async () => { try { await fn(); } catch (e) { alert(api.errMsg(e)); } refreshSources(); };
  const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-4xl space-y-6 p-4 md:p-8">
      <h1 className="text-2xl font-bold">Documents &amp; sources</h1>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card"><h2 className="mb-3 font-semibold">Upload PDFs</h2><FileUpload /></section>
        <section className="card"><h2 className="mb-3 font-semibold">Add a website</h2><WebsiteInput /></section>
      </div>

      <section className="space-y-2">
        <h2 className="font-semibold">PDF documents ({documents.length})</h2>
        {documents.length === 0 && <p className="text-sm text-slate-500">Nothing uploaded yet.</p>}
        {documents.map((d) => (
          <Row key={d.id} icon={FileText} item={d} title={d.filename}
            subtitle={`${kb(d.file_size)}${d.page_count ? ` · ${d.page_count} pages` : ""}${d.chunk_count ? ` · ${d.chunk_count} chunks` : ""}`}
            onAsk={() => go(d.id)} onSummarize={() => go(d.id, `Summarize the document "${d.filename}" and list its key points.`)}
            onReprocess={run(() => api.reprocessDocument(d.id))} onDelete={run(() => api.deleteDocument(d.id))} />
        ))}
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">Websites ({websites.length})</h2>
        {websites.length === 0 && <p className="text-sm text-slate-500">No websites added yet.</p>}
        {websites.map((w) => (
          <Row key={w.id} icon={Globe} item={w} title={w.title || w.url} subtitle={`${w.url}${w.chunk_count ? ` · ${w.chunk_count} chunks` : ""}`}
            onAsk={() => go(w.id)} onSummarize={() => go(w.id, `Summarize the website "${w.title || w.url}" and list its key points.`)}
            onDelete={run(() => api.deleteWebsite(w.id))} />
        ))}
      </section>
    </motion.div>
  );
}
