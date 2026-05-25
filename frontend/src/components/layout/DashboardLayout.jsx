import { useState } from "react";
import { Navigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useAuth } from "../../hooks/useAuth";

export default function DashboardLayout({ children }) {
  const { user, isLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F5F5] dark:bg-[#040f1a]">
        <p className="text-sm text-[#0A2540]/60 dark:text-white/60">Chargement…</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-[#F5F5F5] dark:bg-[#040f1a]">
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <Topbar onToggleSidebar={() => setMobileOpen((o) => !o)} />
      <main className="md:ml-60 min-h-screen px-4 md:px-8 pt-20 md:pt-24 pb-8">{children}</main>
    </div>
  );
}
