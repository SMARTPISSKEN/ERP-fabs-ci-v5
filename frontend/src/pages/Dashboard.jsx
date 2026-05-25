import { useEffect, useState } from "react";
import axios from "axios";
import DashboardLayout from "../components/layout/DashboardLayout";
import { useAuth } from "../hooks/useAuth";
import { COMPANY, ROLES } from "../constants/company";
import KpiCard from "../components/dashboard/KpiCard";
import TreasuryAlert from "../components/dashboard/TreasuryAlert";
import {
  VentesLineChart,
  VentesCategorieBarChart,
  PaiementsPieChart,
  TopClientsBarChart,
} from "../components/dashboard/Charts";

const API = "/api";  // Use relative path with proxy

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const r = await axios.get(`${API}/dashboard/stats`);
        if (!cancelled) setStats(r.data);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || "Erreur de chargement.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const kpiCount = stats?.kpis?.length || 0;
  const kpiCols =
    kpiCount === 1 ? "grid-cols-1" :
    kpiCount === 2 ? "grid-cols-1 sm:grid-cols-2" :
    kpiCount === 3 ? "grid-cols-1 sm:grid-cols-3" :
    kpiCount === 4 ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" :
    "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6";

  return (
    <DashboardLayout>
      <div data-testid="dashboard-page" className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between mb-6 gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#FF6200] font-semibold">
              Tableau de bord
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-[#0A2540] dark:text-white mt-1">
              Bonjour, {user?.nom_complet?.split(" ")[0] || "Bienvenue"}.
            </h1>
            <p className="text-sm text-gray-600 dark:text-white/60 mt-1">
              Vue d'ensemble de l'activité — Année scolaire {COMPANY.anneeScolaire}.
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-wider text-gray-400 dark:text-white/40">
              Votre rôle
            </p>
            <p
              data-testid="dashboard-role"
              className="text-sm font-semibold text-[#0A2540] dark:text-white mt-0.5"
            >
              {ROLES[user?.role] || user?.role}
            </p>
          </div>
        </div>

        {/* Demo data banner */}
        {stats?.is_demo_data && (
          <div
            data-testid="demo-data-banner"
            className="mb-5 text-[11px] uppercase tracking-wider bg-[#0A2540]/5 dark:bg-white/5 text-[#0A2540] dark:text-white/70 border border-[#0A2540]/10 dark:border-white/10 rounded-lg px-4 py-2"
          >
            ⓘ Données de démonstration — connectées aux modules métier dès le Sprint 4.
          </div>
        )}

        {loading && (
          <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-10 text-center text-sm text-gray-500 dark:text-white/50">
            Chargement des statistiques…
          </div>
        )}

        {error && (
          <div
            data-testid="dashboard-error"
            className="bg-red-50 border border-[#C62828]/30 text-[#C62828] rounded-lg p-4 text-sm"
          >
            {error}
          </div>
        )}

        {stats && !loading && (
          <>
            {/* Treasury alert (bonus, role-gated server-side) */}
            {stats.treasury_alert?.depasse && (
              <div className="mb-5">
                <TreasuryAlert data={stats.treasury_alert} />
              </div>
            )}

            {/* KPI Grid */}
            <div data-testid="kpi-grid" className={`grid ${kpiCols} gap-5 mb-8`}>
              {stats.kpis.map((kpi) => (
                <KpiCard key={kpi.key} kpi={kpi} />
              ))}
            </div>

            {/* Charts Grid */}
            {(stats.charts?.ventes_12_mois || stats.charts?.ventes_categorie ||
              stats.charts?.paiements_mode || stats.charts?.top_clients) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {stats.charts.ventes_12_mois && (
                  <div className="lg:col-span-2">
                    <VentesLineChart data={stats.charts.ventes_12_mois} />
                  </div>
                )}
                {stats.charts.ventes_categorie && (
                  <VentesCategorieBarChart data={stats.charts.ventes_categorie} />
                )}
                {stats.charts.paiements_mode && (
                  <PaiementsPieChart data={stats.charts.paiements_mode} />
                )}
                {stats.charts.top_clients && (
                  <div className="lg:col-span-2">
                    <TopClientsBarChart data={stats.charts.top_clients} />
                  </div>
                )}
              </div>
            )}

            {/* Roles without any chart get a contextual info card */}
            {!(stats.charts?.ventes_12_mois || stats.charts?.paiements_mode ||
               stats.charts?.top_clients) && (
              <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-6 shadow-sm">
                <h2 className="text-lg font-bold text-[#0A2540] dark:text-white">
                  Votre espace de travail
                </h2>
                <p className="text-sm text-gray-600 dark:text-white/60 mt-2 leading-relaxed">
                  Vos indicateurs clés sont affichés ci-dessus. Les modules métier accessibles
                  à votre rôle apparaissent dans la barre latérale gauche.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
