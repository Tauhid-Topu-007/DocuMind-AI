import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";
import { Check, Copy, TriangleAlert } from "lucide-react";
import SourceCitation from "../SourceCitation/SourceCitation.jsx";
import useCopy from "../../hooks/useCopy.js";

export default function MessageBubble({ message }) {
  const { copied, copy } = useCopy();
  const isUser = message.role === "user";
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed md:max-w-[80%] ${isUser ? "bg-indigo-500 text-white" : "border border-slate-800 bg-slate-900"}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div className={`md ${message.streaming ? "caret" : ""}`}>
              <ReactMarkdown>{message.content || (message.streaming ? "" : "")}</ReactMarkdown>
            </div>
            {message.error && (
              <p className="mt-2 flex items-start gap-2 text-red-300"><TriangleAlert size={16} className="mt-0.5 shrink-0" /> {message.error}</p>
            )}
            {!message.streaming && <SourceCitation sources={message.sources} />}
            {!message.streaming && message.content && (
              <button onClick={() => copy(message.content)} className="mt-2 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">
                {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? "Copied" : "Copy"}
              </button>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}
