import { useState } from "react";
import { Send, Square } from "lucide-react";

export default function ChatInput({ onSend, onStop, loading }) {
  const [text, setText] = useState("");
  const submit = () => {
    if (!text.trim() || loading) return;
    onSend(text);
    setText("");
  };
  return (
    <div className="flex items-end gap-2 rounded-2xl border border-slate-700 bg-slate-900 p-2 focus-within:border-indigo-500">
      <textarea
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); }
        }}
        placeholder="Ask about your documents and websites…"
        className="max-h-40 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder-slate-500"
      />
      {loading ? (
        <button className="btn btn-ghost !px-3" onClick={onStop} aria-label="Stop"><Square size={16} /></button>
      ) : (
        <button className="btn btn-primary !px-3" onClick={submit} disabled={!text.trim()} aria-label="Send"><Send size={16} /></button>
      )}
    </div>
  );
}
