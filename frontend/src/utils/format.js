// Formatage FCFA — séparateur d'espaces, sans décimale.
export function formatFCFA(amount, withSuffix = true) {
  if (amount == null || isNaN(amount)) return "—";
  const formatted = Number(amount)
    .toLocaleString("fr-FR", { maximumFractionDigits: 0 })
    .replace(/,/g, " ");
  return withSuffix ? `${formatted} FCFA` : formatted;
}

// Compact "1,2 M" / "850 K" pour KPIs
export function formatFCFACompact(amount) {
  if (amount == null || isNaN(amount)) return "—";
  const n = Number(amount);
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(0)} K`;
  return String(n);
}
