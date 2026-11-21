import { useApp } from "../../context/AppContext.jsx";

export default function ModelSelector({ compact = false }) {
  const { model, setModel, modelsInfo } = useApp();
  const provider = model.provider || "";
  const list = provider === "ollama" ? modelsInfo?.ollama?.models : provider === "groq" ? modelsInfo?.groq?.models : [];
  const def = provider === "ollama" ? modelsInfo?.ollama?.default : provider === "groq" ? modelsInfo?.groq?.default : "";
  const cls = `input ${compact ? "!w-auto !py-1.5" : ""}`;
  return (
    <div className={`flex ${compact ? "items-center gap-2" : "flex-col gap-3 sm:flex-row"}`}>
      <select className={cls} value={provider} onChange={(e) => setModel({ provider: e.target.value || null, model: null })} aria-label="Inference mode">
        <option value="">Server default</option>
        <option value="ollama">Local · Ollama</option>
        <option value="groq">Cloud · Groq</option>
      </select>
      {provider && (
        <select className={cls} value={model.model || ""} onChange={(e) => setModel({ ...model, model: e.target.value || null })} aria-label="Model">
          <option value="">{def ? `Default (${def})` : "Default model"}</option>
          {(list || []).filter((m) => m !== def).map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      )}
    </div>
  );
}
