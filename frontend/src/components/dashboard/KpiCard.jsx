import {
  TrendingUp, TrendingDown, AlertCircle, CheckCircle, ShoppingCart,
  Package, Truck, Wallet, Users, RotateCcw, Activity,
} from "lucide-react";
import { formatFCFA, formatFCFACompact } from "../../utils/format";

const ICONS = {
  TrendingUp, AlertCircle, CheckCircle, ShoppingCart, Package, Truck,
  Wallet, Users, RotateCcw, Activity,
};

export default function KpiCard({ kpi }) {
  const Icon = ICONS[kpi.icon] || Activity;
  const variation = kpi.variation_pct ?? 0;
  const variationPositive = variation > 0;
  const variationNeutral = variation === 0;
  const VarIcon = variationPositive ? TrendingUp : TrendingDown;

  const isCurrency = kpi.suffix === "FCFA";

  return (
    <div
      data-testid={`kpi-${kpi.key}`}
      className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-5 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: `${kpi.accent}18` }}
        >
          <Icon className="w-5 h-5" style={{ color: kpi.accent }} />
        </div>
        {!variationNeutral && (
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              variationPositive
                ? "bg-[#2E7D32]/10 text-[#2E7D32]"
                : "bg-[#C62828]/10 text-[#C62828]"
            }`}
          >
            <VarIcon className="w-3 h-3" />
            {variationPositive ? "+" : ""}
            {variation.toFixed(1).replace(".", ",")}%
          </span>
        )}
      </div>
      <p className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-white/50 mt-4">
        {kpi.label}
      </p>
      <p className="text-2xl font-bold text-[#0A2540] dark:text-white mt-1 tracking-tight">
        {isCurrency ? formatFCFACompact(kpi.value) : kpi.value.toLocaleString("fr-FR")}
        {kpi.suffix && (
          <span className="text-xs text-gray-400 dark:text-white/40 ml-1 font-medium">
            {kpi.suffix === "FCFA" ? "FCFA" : kpi.suffix}
          </span>
        )}
      </p>
      {kpi.secondary_value != null && (
        <p className="text-[11px] text-gray-500 dark:text-white/50 mt-1">
          dont {formatFCFA(kpi.secondary_value)} dû
        </p>
      )}
    </div>
  );
}
