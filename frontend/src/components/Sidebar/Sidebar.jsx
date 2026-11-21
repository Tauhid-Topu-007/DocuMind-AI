import { NavLink, useNavigate } from "react-router-dom";
import { BrainCircuit, FileText, LayoutDashboard, MessageSquare, Plus, Settings, Trash2, X } from "lucide-react";
import { useApp } from "../../context/AppContext.jsx";
import * as api from "../../services/api";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar({ open, onClose }) {
  const navigate = useNavigate();
  const { conversations, refreshConversations } = useApp();

  const newChat = () => {
    navigate("/chat", { state: { fresh: Date.now() } });
    onClose();
  };
  const remove = async (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    await api.deleteConversation(id).catch(() => {});
    await refreshConversations();
    if (window.location.pathname.endsWith(id)) navigate("/chat", { state: { fresh: Date.now() } });
  };
  const link = ({ isActive }) =>
    `flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${isActive ? "bg-indigo-500/15 text-indigo-200" : "text-slate-300 hover:bg-slate-800"}`;

  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={onClose} />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800 bg-slate-950 p-3 transition-transform md:static md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="mb-4 flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2 text-lg font-semibold">
            <BrainCircuit className="text-indigo-400" /> DocuMind AI
          </div>
          <button className="rounded-lg p-1 hover:bg-slate-800 md:hidden" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <button className="btn btn-primary mb-3 w-full" onClick={newChat}>
          <Plus size={16} /> New chat
        </button>

        <nav className="space-y-1" onClick={onClose}>
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={link}>
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>

        <div className="mb-2 mt-5 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Conversations</div>
        <div className="-mr-1 min-h-0 flex-1 space-y-1 overflow-y-auto pr-1" onClick={onClose}>
          {conversations.length === 0 && <p className="px-2 text-sm text-slate-500">No conversations yet.</p>}
          {conversations.map((c) => (
            <NavLink key={c.id} to={`/chat/${c.id}`} className={(s) => `group ${link(s)}`}>
              <MessageSquare size={16} className="shrink-0" />
              <span className="min-w-0 flex-1 truncate">{c.title}</span>
              <button
                className="hidden rounded p-1 text-slate-400 hover:bg-slate-700 hover:text-red-300 group-hover:block"
                onClick={(e) => remove(e, c.id)}
                aria-label="Delete conversation"
              >
                <Trash2 size={14} />
              </button>
            </NavLink>
          ))}
        </div>
      </aside>
    </>
  );
}
