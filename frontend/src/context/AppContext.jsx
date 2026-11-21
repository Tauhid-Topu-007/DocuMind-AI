import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as api from "../services/api";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

const loadModel = () => {
  try {
    return JSON.parse(localStorage.getItem("documind_model")) || { provider: null, model: null };
  } catch {
    return { provider: null, model: null };
  }
};

export function AppProvider({ children }) {
  const [documents, setDocuments] = useState([]);
  const [websites, setWebsites] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [modelsInfo, setModelsInfo] = useState(null);
  const [backendError, setBackendError] = useState(null);
  const [model, setModelState] = useState(loadModel);

  const setModel = useCallback((m) => {
    setModelState(m);
    localStorage.setItem("documind_model", JSON.stringify(m));
  }, []);

  const refreshSources = useCallback(async () => {
    try {
      const [d, w] = await Promise.all([api.listDocuments(), api.listWebsites()]);
      setDocuments(d);
      setWebsites(w);
      setBackendError(null);
    } catch (e) {
      setBackendError(api.errMsg(e));
    }
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch {}
  }, []);

  const loadModels = useCallback(async () => {
    try {
      setModelsInfo(await api.getModels());
    } catch {}
  }, []);

  useEffect(() => {
    refreshSources();
    refreshConversations();
    loadModels();
  }, [refreshSources, refreshConversations, loadModels]);

  // Poll while anything is still being processed.
  const processing = documents.some((d) => d.status === "processing") || websites.some((w) => w.status === "processing");
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(refreshSources, 2500);
    return () => clearInterval(t);
  }, [processing, refreshSources]);

  const readySources = useMemo(
    () => [
      ...documents.filter((d) => d.status === "processed").map((d) => ({ id: d.id, name: d.filename, type: "pdf" })),
      ...websites.filter((w) => w.status === "processed").map((w) => ({ id: w.id, name: w.title || w.url, type: "website" })),
    ],
    [documents, websites]
  );
  const activeIds = useMemo(() => selectedIds.filter((id) => readySources.some((s) => s.id === id)), [selectedIds, readySources]);

  const value = {
    documents, websites, conversations, readySources,
    selectedIds, setSelectedIds, activeIds,
    model, setModel, modelsInfo, loadModels,
    backendError, refreshSources, refreshConversations,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
