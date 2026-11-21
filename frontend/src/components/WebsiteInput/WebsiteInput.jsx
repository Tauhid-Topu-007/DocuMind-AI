import { useState } from "react";
import { Globe, Loader2 } from "lucide-react";
import { errMsg, ingestWebsite } from "../../services/api";
import { useApp } from "../../context/AppContext.jsx";

export default function WebsiteInput() {
  const { refreshSources } = useApp();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setError("");
    setOk(false);
    try {
      await ingestWebsite(url.trim());
      setUrl("");
      setOk(true);
      refreshSources();
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Globe size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input pl-9" placeholder="https://example.com/article" value={url} onChange={(e) => setUrl(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={busy || !url.trim()}>
          {busy ? <Loader2 size={16} className="animate-spin" /> : "Add"}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
      {ok && <p className="mt-2 text-sm text-emerald-300">Added. Extracting and indexing…</p>}
      <p className="mt-2 text-xs text-slate-500">Public HTML pages only. JavaScript-rendered, login-protected or bot-blocking sites may fail.</p>
    </form>
  );
}
