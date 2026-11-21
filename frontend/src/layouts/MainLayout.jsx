import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu, TriangleAlert } from "lucide-react";
import Sidebar from "../components/Sidebar/Sidebar.jsx";
import { useApp } from "../context/AppContext.jsx";

export default function MainLayout() {
  const [open, setOpen] = useState(false);
  const { backendError } = useApp();
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-slate-800 px-3 py-2 md:hidden">
          <button className="rounded-lg p-2 hover:bg-slate-800" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <span className="font-semibold">DocuMind AI</span>
        </div>
        {backendError && (
          <div className="flex items-center gap-2 bg-amber-500/10 px-4 py-2 text-sm text-amber-300">
            <TriangleAlert size={16} /> {backendError}
          </div>
        )}
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
