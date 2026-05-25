import { AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";

export default function StockBadge({ statut, stock_actuel, stock_minimum }) {
  if (statut === "rupture") {
    return (
      <span
        data-testid={`stock-badge-rupture`}
        className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-[#C62828]/15 text-[#C62828]"
      >
        <AlertCircle className="w-3 h-3" />
        Rupture
      </span>
    );
  }
  if (statut === "alerte") {
    return (
      <span
        data-testid={`stock-badge-alerte`}
        className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-[#FF6200]/15 text-[#FF6200]"
        title={`Stock ${stock_actuel} ≤ minimum ${stock_minimum}`}
      >
        <AlertTriangle className="w-3 h-3" />
        Alerte
      </span>
    );
  }
  return (
    <span
      data-testid={`stock-badge-ok`}
      className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-[#2E7D32]/12 text-[#2E7D32]"
    >
      <CheckCircle2 className="w-3 h-3" />
      OK
    </span>
  );
}
