import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Mail, Lock, Loader2 } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import Logo from "../components/Logo";
import { COMPANY } from "../constants/company";

function formatApiErrorDetail(detail) {
  if (detail == null) return "Une erreur est survenue. Veuillez réessayer.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default function Login() {
  const { user, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0A2540] to-[#040f1a]">
        <p className="text-white/60 text-sm">Chargement…</p>
      </div>
    );
  }
  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Email et mot de passe requis");
      return;
    }
    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-[#0A2540] via-[#0a2540] to-[#040f1a] flex items-center justify-center px-4">
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
        className="absolute -top-32 -right-32 w-96 h-96 rounded-full blur-3xl opacity-30"
        style={{ background: "#FF6200" }}
      />

      <div
        data-testid="login-card"
        className="relative z-10 bg-white shadow-2xl rounded-2xl p-10 max-w-md w-full mx-auto"
      >
        <div className="flex flex-col items-center gap-2 mb-8">
          <Logo variant="light" size="lg" />
          <p className="text-xs uppercase tracking-[0.2em] text-[#0A2540]/60 mt-3">
            ERP — Année scolaire {COMPANY.anneeScolaire}
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <h1 className="text-2xl font-bold text-[#0A2540] tracking-tight text-center">
            Connexion à votre espace
          </h1>

          {error && (
            <div
              data-testid="login-error"
              className="bg-red-50 border border-[#C62828]/30 text-[#C62828] text-sm rounded-lg px-4 py-3"
            >
              {error}
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-[#0A2540] mb-1.5 block">Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                data-testid="login-email-input"
                type="email"
                placeholder="vous@editionsfabsci.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                className="w-full pl-9 pr-3 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200] text-[#0A2540]"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-[#0A2540] mb-1.5 block">Mot de passe</label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                data-testid="login-password-input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="w-full pl-9 pr-3 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200] text-[#0A2540]"
              />
            </div>
          </div>

          <button
            data-testid="login-submit-btn"
            type="submit"
            disabled={submitting}
            className="w-full bg-[#FF6200] hover:bg-[#E65800] active:bg-[#CC4F00] disabled:opacity-60 disabled:cursor-not-allowed transition-colors text-white py-3 rounded-lg font-semibold flex items-center justify-center gap-3 shadow-md hover:shadow-lg"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connexion…
              </>
            ) : (
              "Se connecter"
            )}
          </button>

          <div className="pt-2 border-t border-gray-100">
            <p className="text-[11px] uppercase tracking-wider text-gray-400 text-center">
              {COMPANY.nom} · {COMPANY.dg} (DG)
            </p>
          </div>
        </form>
      </div>

      <p
        className="absolute bottom-6 left-0 right-0 text-center text-[#F5F5F5]/60 text-xs italic px-4"
        data-testid="login-slogan"
      >
        « {COMPANY.slogan} »
      </p>
    </div>
  );
}
