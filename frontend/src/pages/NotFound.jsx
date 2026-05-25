import { Link } from "react-router-dom";
import Logo from "../components/Logo";
import { Home } from "lucide-react";
import { COMPANY } from "../constants/company";

export default function NotFound() {
  return (
    <div
      data-testid="not-found-page"
      className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0A2540] via-[#0a2540] to-[#040f1a] px-4 relative overflow-hidden"
    >
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.07] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(#FFFFFF 1px, transparent 1px), linear-gradient(90deg, #FFFFFF 1px, transparent 1px)",
          backgroundSize: "44px 44px",
        }}
      />
      <div
        aria-hidden
        className="absolute -top-32 -left-32 w-96 h-96 rounded-full blur-3xl opacity-20"
        style={{ background: "#FF6200" }}
      />

      <div className="relative z-10 text-center max-w-lg">
        <div className="bg-white rounded-2xl p-8 shadow-2xl">
          <div className="flex justify-center mb-6">
            <Logo variant="light" size="md" />
          </div>
          <p className="text-[11px] uppercase tracking-[0.25em] text-[#FF6200] font-semibold">
            Erreur 404
          </p>
          <h1 className="text-3xl font-bold text-[#0A2540] tracking-tight mt-2">
            Page introuvable
          </h1>
          <p className="text-sm text-gray-600 mt-3">
            La page que vous recherchez n'existe pas ou a été déplacée.
          </p>
          <Link
            to="/dashboard"
            data-testid="not-found-home-btn"
            className="inline-flex items-center gap-2 mt-6 px-5 py-2.5 rounded-lg bg-[#FF6200] hover:bg-[#E65800] text-white text-sm font-semibold shadow-md hover:shadow-lg transition"
          >
            <Home className="w-4 h-4" />
            Retour au tableau de bord
          </Link>
        </div>
        <p className="mt-6 text-[#F5F5F5]/60 text-xs italic">
          « {COMPANY.slogan} »
        </p>
      </div>
    </div>
  );
}
