import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FileText, Globe, MessageSquare } from "lucide-react";
import FileUpload from "../components/FileUpload/FileUpload.jsx";
import WebsiteInput from "../components/WebsiteInput/WebsiteInput.jsx";
import { useApp } from "../context/AppContext.jsx";

export default function Dashboard() {
  const { documents, websites, conversations, readySources } = useApp();
  const stats = [
    { label: "PDF documents", value: documents.length, icon: FileText },
    { label: "Websites", value: websites.length, icon: Globe },
    { label: "Conversations", value: conversations.length, icon: MessageSquare },
  ];
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-5xl space-y-6 p-4 md:p-8">
      <div>
        <h1 className="text-2xl font-bold">DocuMind AI</h1>
        <p className="mt-1 text-slate-400">Your documents. Your web. One intelligent assistant.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="card flex items-center gap-4">
            <div className="rounded-xl bg-indigo-500/15 p-3 text-indigo-300"><Icon size={22} /></div>
            <div><div className="text-2xl font-semibold">{value}</div><div className="text-sm text-slate-400">{label}</div></div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card"><h2 className="mb-3 font-semibold">Upload PDFs</h2><FileUpload /></section>
        <section className="card"><h2 className="mb-3 font-semibold">Add a website</h2><WebsiteInput /></section>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link to="/chat" className="btn btn-primary">Start chatting {readySources.length ? `(${readySources.length} ready)` : ""}</Link>
        <Link to="/documents" className="btn btn-ghost">Manage sources</Link>
      </div>
    </motion.div>
  );
}
