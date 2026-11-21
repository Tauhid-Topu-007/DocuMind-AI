import axios from "axios";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

// Anonymous per-browser id. The backend scopes every document/conversation by it.
export function getUserId() {
  let id = localStorage.getItem("documind_user_id");
  if (!id) {
    const raw = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}${Math.random().toString(36).slice(2)}`;
    id = raw.replace(/[^A-Za-z0-9_-]/g, "");
    localStorage.setItem("documind_user_id", id);
  }
  return id;
}

const client = axios.create({ baseURL: API_BASE, timeout: 60000 });
client.interceptors.request.use((cfg) => {
  cfg.headers["X-User-Id"] = getUserId();
  return cfg;
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join("; ");
  if (e?.code === "ERR_NETWORK") return "Cannot reach the backend. Is it running and is CORS configured?";
  return e?.message || "Something went wrong";
}

const data = (p) => p.then((r) => r.data);

export const listDocuments = () => data(client.get("/documents"));
export const uploadDocument = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return data(client.post("/documents/upload", fd, { timeout: 180000 }));
};
export const deleteDocument = (id) => data(client.delete(`/documents/${id}`));
export const reprocessDocument = (id) => data(client.post(`/documents/${id}/reprocess`));

export const listWebsites = () => data(client.get("/websites"));
export const ingestWebsite = (url) => data(client.post("/websites/ingest", { url }));
export const deleteWebsite = (id) => data(client.delete(`/websites/${id}`));

export const listConversations = () => data(client.get("/conversations"));
export const getConversation = (id) => data(client.get(`/conversations/${id}`));
export const deleteConversation = (id) => data(client.delete(`/conversations/${id}`));

export const getModels = () => data(client.get("/models"));
export const getProviders = () => data(client.get("/models/providers"));
export const selectModel = (provider, model) => data(client.post("/models/select", { provider, model }));
export const getHealth = () => data(client.get("/health"));

// Streaming uses fetch (axios cannot stream in the browser).
export async function streamChat({ question, conversationId, sourceIds, provider, model, signal, onMeta, onSources, onToken, onError }) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Id": getUserId() },
    body: JSON.stringify({ question, conversation_id: conversationId, source_ids: sourceIds || [], provider, model }),
    signal,
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : j.detail?.map((x) => x.msg).join("; ") || msg;
    } catch {}
    throw new Error(msg);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  const dispatch = (block) => {
    let event = "message";
    let payload = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) payload += line.slice(5).trim();
    }
    if (!payload) return;
    const d = JSON.parse(payload);
    if (event === "meta") onMeta?.(d);
    else if (event === "sources") onSources?.(d);
    else if (event === "token") onToken?.(d.text);
    else if (event === "error") onError?.(d.message);
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) !== -1) {
      dispatch(buf.slice(0, i));
      buf = buf.slice(i + 2);
    }
  }
}
