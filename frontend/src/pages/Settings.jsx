import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy } from "lucide-react";
import ModelSelector from "../components/ModelSelector/ModelSelector.jsx";
import { useApp } from "../context/AppContext.jsx";
import useCopy from "../hooks/useCopy.js";
import * as api from "../services/api";

export default function Settings() {
  const { model, modelsInfo, loadModels } = useApp();
  const { copied, copy } = useCopy();
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadModels();
    api.getHealth().then(setHealth).catch((e) => setErr(api.errMsg(e)));
  }, [loadModels]);

  const saveDefault = async () => {
    if (!model.provider) return;
    try { await api.selectModel(model.provider, model.model); setSaved(true); setTimeout(() => setSaved(false), 1500); loadModels(); }
    catch (e) { setErr(api.errMsg(e)); }
  };

  const dot = (ok) => <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-slate-600"}`} />;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-3xl space-y-6 p-4 md:p-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      <section className="card space-y-3">
        <h2 className="font-semibold">Inference</h2>
        <p className="text-sm text-slate-400">Your choice is saved in this browser and sent with every question. Production servers cannot reach your local Ollama, so use Groq there.</p>
        <ModelSelector />
        <button className="btn btn-ghost" onClick={saveDefault} disabled={!model.provider}>{saved ? "Saved" : "Also set as server default (this session)"}</button>
        <ul className="space-y-1 text-sm text-slate-300">
          <li className="flex items-center gap-2">{dot(modelsInfo?.ollama?.available)} Ollama {modelsInfo?.ollama?.available ? `reachable · ${modelsInfo.ollama.models.length} chat model(s)` : "not reachable from the backend"}</li>
          <li className="flex items-center gap-2">{dot(modelsInfo?.groq?.configured)} Groq {modelsInfo?.groq?.configured ? `configured · default ${modelsInfo.groq.default || "(set GROQ_MODEL)"}` : "not configured (set GROQ_API_KEY and GROQ_MODEL)"}</li>
        </ul>
      </section>

      <section className="card space-y-2 text-sm">
        <h2 className="font-semibold">Backend</h2>
        <p className="break-all text-slate-400">API: {api.API_BASE}</p>
        {err && <p className="text-red-300">{err}</p>}
        {health && (
          <p className="text-slate-300">
            {health.app} · env <b>{health.env}</b> · embeddings <b>{health.embedding_provider}</b> · vectors <b>{health.vector_db}</b> · metadata <b>{health.database}</b>
          </p>
        )}
      </section>

      <section className="card space-y-2 text-sm">
        <h2 className="font-semibold">Your browser id</h2>
        <p className="text-slate-400">Documents and chats are tied to this anonymous id. Clearing site data creates a new, empty workspace.</p>
        <button className="btn btn-ghost" onClick={() => copy(api.getUserId())}>{copied ? <Check size={14} /> : <Copy size={14} />} {api.getUserId()}</button>
      </section>
    </motion.div>
  );
}
