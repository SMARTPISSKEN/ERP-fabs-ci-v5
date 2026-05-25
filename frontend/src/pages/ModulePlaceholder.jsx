import DashboardLayout from "../components/layout/DashboardLayout";
import { Construction } from "lucide-react";

/**
 * Placeholder pour les modules métier livrés dans les sprints suivants.
 * Affiche un état "en construction" propre, fidèle au design system.
 */
export default function ModulePlaceholder({ title, sprint, description }) {
  return (
    <DashboardLayout>
      <div
        data-testid={`placeholder-${title.toLowerCase().replace(/\s+/g, "-")}`}
        className="max-w-3xl mx-auto"
      >
        <div className="bg-white dark:bg-white/5 rounded-2xl border border-gray-200 dark:border-white/10 shadow-sm p-10 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#FF6200]/10 mb-6">
            <Construction className="w-8 h-8 text-[#FF6200]" />
          </div>
          <p className="text-[11px] uppercase tracking-[0.25em] text-[#FF6200] font-semibold">
            {sprint}
          </p>
          <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white tracking-tight mt-2">
            {title}
          </h1>
          <p className="text-sm text-gray-600 dark:text-white/60 mt-3 max-w-md mx-auto">
            {description}
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
