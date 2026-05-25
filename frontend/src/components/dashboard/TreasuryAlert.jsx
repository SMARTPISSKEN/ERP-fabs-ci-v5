import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { formatFCFA } from "../../utils/format";

/**
 * Bonus — bannière "Trésorerie" : alerte si total créances > seuil.
 * Affiche un CTA dépliable qui liste les factures à relancer triées par
 * jours de retard décroissants.
 */
export default function TreasuryAlert({ data }) {
  const [open, setOpen] = useState(false);
  if (!data) return null;

  const { total_creances, seuil_fcfa, depasse, factures_a_relancer = [] } = data;
  if (!depasse) return null;

  return (
    <div
      data-testid="treasury-alert"
      className="rounded-xl border-2 border-[#FF6200]/30 bg-gradient-to-r from-[#FF6200]/8 via-[#FF6200]/4 to-transparent dark:from-[#FF6200]/20 dark:via-[#FF6200]/10 dark:to-transparent p-5 shadow-sm"
    >
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 shrink-0 rounded-xl bg-[#FF6200]/15 flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-[#FF6200]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <p className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#FF6200]">
              Alerte Trésorerie
            </p>
            <p className="text-[11px] text-gray-500 dark:text-white/50">
              Seuil paramétré : {formatFCFA(seuil_fcfa)}
            </p>
          </div>
          <h3 className="text-base font-bold text-[#0A2540] dark:text-white mt-1">
            Vos créances clients ({formatFCFA(total_creances)}) dépassent le seuil de pilotage.
          </h3>
          <p className="text-sm text-gray-600 dark:text-white/70 mt-1">
            {factures_a_relancer.length} facture{factures_a_relancer.length > 1 ? "s" : ""} à
            relancer, triée{factures_a_relancer.length > 1 ? "s" : ""} par retard décroissant.
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              data-testid="treasury-toggle-btn"
              onClick={() => setOpen((o) => !o)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#FF6200] hover:bg-[#E65800] text-white text-xs font-semibold uppercase tracking-wider shadow-sm transition-colors"
            >
              {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {open ? "Masquer" : "Voir les factures à relancer"}
            </button>
          </div>

          {open && (
            <div
              data-testid="treasury-table"
              className="mt-4 overflow-x-auto rounded-lg border border-[#FF6200]/20 bg-white dark:bg-[#0A2540]"
            >
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#FF6200]/8 dark:bg-white/5 text-[10px] uppercase tracking-wider text-[#0A2540] dark:text-white/70">
                    <th className="text-left px-3 py-2 font-semibold">Référence</th>
                    <th className="text-left px-3 py-2 font-semibold">Client</th>
                    <th className="text-right px-3 py-2 font-semibold">Montant</th>
                    <th className="text-right px-3 py-2 font-semibold">Retard</th>
                  </tr>
                </thead>
                <tbody>
                  {factures_a_relancer.map((f) => (
                    <tr
                      key={f.reference}
                      data-testid={`treasury-row-${f.reference}`}
                      className="border-t border-gray-100 dark:border-white/10"
                    >
                      <td className="px-3 py-2 font-mono text-[11px] text-[#0A2540] dark:text-white/90 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <FileText className="w-3 h-3 text-gray-400 dark:text-white/40" />
                          {f.reference}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-gray-700 dark:text-white/80">{f.client}</td>
                      <td className="px-3 py-2 text-right font-semibold text-[#0A2540] dark:text-white whitespace-nowrap">
                        {formatFCFA(f.montant)}
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold ${
                            f.jours_retard >= 45
                              ? "bg-[#C62828]/15 text-[#C62828]"
                              : f.jours_retard >= 15
                              ? "bg-[#FF6200]/15 text-[#FF6200]"
                              : "bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-white/70"
                          }`}
                        >
                          {f.jours_retard} j
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
