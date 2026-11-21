import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit } from "lucide-react";
import MessageBubble from "../components/Chat/MessageBubble.jsx";
import ChatInput from "../components/Chat/ChatInput.jsx";
import SourcePicker from "../components/Chat/SourcePicker.jsx";
import ModelSelector from "../components/ModelSelector/ModelSelector.jsx";
import { useApp } from "../context/AppContext.jsx";
import { getConversation, streamChat } from "../services/api";

const SUGGESTIONS = [
  "Summarize the key points of my documents",
  "What methodology is used?",
  "What are the main limitations or risks mentioned?",
];

export default function ChatPage() {
  const { conversationId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { activeIds, setSelectedIds, model, refreshConversations, readySources } = useApp();

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const convRef = useRef(conversationId || null);
  const skipLoad = useRef(null);
  const abortRef = useRef(null);
  const handledKey = useRef(null);
  const bottomRef = useRef(null);

  // Load an existing conversation, or reset for a new one.
  useEffect(() => {
    if (conversationId) {
      if (skipLoad.current === conversationId) { skipLoad.current = null; return; }
      abortRef.current?.abort();
      convRef.current = conversationId;
      getConversation(conversationId).then((r) => setMessages(r.messages)).catch(() => navigate("/chat", { replace: true }));
    } else {
      abortRef.current?.abort();
      convRef.current = null;
      setMessages([]);
    }
  }, [conversationId, location.state?.fresh]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);

  const send = async (text, idsOverride) => {
    const q = text.trim();
    if (!q || loading) return;
    setLoading(true);
    setMessages((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "", sources: [], streaming: true }]);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const patchLast = (fn) => setMessages((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c; });
    try {
      await streamChat({
        question: q,
        conversationId: convRef.current,
        sourceIds: idsOverride ?? activeIds,
        provider: model.provider,
        model: model.model,
        signal: ctrl.signal,
        onMeta: (d) => {
          if (!convRef.current) {
            convRef.current = d.conversation_id;
            skipLoad.current = d.conversation_id;
            navigate(`/chat/${d.conversation_id}`, { replace: true });
          }
        },
        onSources: (d) => patchLast((x) => ({ ...x, sources: d.sources })),
        onToken: (t) => patchLast((x) => ({ ...x, content: x.content + t })),
        onError: (msg) => patchLast((x) => ({ ...x, error: msg })),
      });
    } catch (e) {
      if (e.name !== "AbortError") patchLast((x) => ({ ...x, error: e.message }));
    } finally {
      patchLast((x) => ({ ...x, streaming: false }));
      setLoading(false);
      refreshConversations();
    }
  };

  // Auto-send when arriving from the Documents page ("Summarize" / "Ask").
  useEffect(() => {
    const st = location.state;
    if (st?.autoPrompt && handledKey.current !== location.key) {
      handledKey.current = location.key;
      if (st.sourceIds) setSelectedIds(st.sourceIds);
      send(st.autoPrompt, st.sourceIds);
    }
  }, [location.key]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-4 py-2">
        <SourcePicker />
        <div className="ml-auto"><ModelSelector compact /></div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-16 text-center">
              <BrainCircuit className="mx-auto mb-3 text-indigo-400" size={40} />
              <h2 className="text-xl font-semibold">Ask anything about your sources</h2>
              <p className="mt-1 text-sm text-slate-400">
                {readySources.length ? `Searching ${activeIds.length || readySources.length} source(s). Answers include citations.` : "Upload a PDF or add a website first (Dashboard → Documents)."}
              </p>
              {readySources.length > 0 && (
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="btn btn-ghost !text-xs" onClick={() => send(s)}>{s}</button>
                  ))}
                </div>
              )}
            </motion.div>
          )}
          {messages.map((m, i) => <MessageBubble key={m.id || i} message={m} />)}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-slate-800 px-4 py-3">
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={send} onStop={() => abortRef.current?.abort()} loading={loading} />
        </div>
      </div>
    </div>
  );
}
