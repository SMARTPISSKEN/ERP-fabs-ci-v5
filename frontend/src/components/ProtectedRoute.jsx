import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { can } from "../constants/permissions";

/**
 * Garde de route : vérifie l'authentification + (optionnel) le rôle autorisé
 * pour le `moduleKey` donné selon la matrice de permissions.
 *
 * Usage:
 *  <ProtectedRoute moduleKey="factures"><Factures /></ProtectedRoute>
 */
export default function ProtectedRoute({ children, moduleKey }) {
  const { user, isLoading, role } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F5F5] dark:bg-[#040f1a]">
        <div className="flex items-center gap-3 text-sm text-[#0A2540]/70 dark:text-white/70">
          <span className="inline-block w-2 h-2 rounded-full bg-[#FF6200] animate-pulse" />
          Vérification…
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (moduleKey && !can(role, moduleKey)) {
    return <Navigate to="/dashboard" replace state={{ forbidden: moduleKey }} />;
  }

  return children;
}
