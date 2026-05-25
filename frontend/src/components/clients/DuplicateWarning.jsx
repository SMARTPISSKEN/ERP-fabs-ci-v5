import { useEffect, useState, useMemo } from "react";
import { AlertTriangle, Phone, X } from "lucide-react";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { checkDuplicates } from "../../services/clientsApi";

/**
 * Live duplicate detection — debounced 400ms.
 * Shown above the form whenever similar clients are detected.
 *
 * Props:
 *  - nom (string)
 *  - telephone (string)
 *  - excludeId (string|null) — when editing, ignore self
 *  - onMatchesChange(matches) — parent can disable submit or pre-populate
 */
export default function DuplicateWarning({ nom, telephone, excludeId, onMatchesChange }) {
  const dNom = useDebouncedValue(nom, 400);
  const dPhone = useDebouncedValue(telephone, 400);
  const [matches, setMatches] = useState([]);
  const [dismissedKey, setDismissedKey] = useState(null);

  const currentKey = useMemo(
    () => `${(dNom || "").trim().toLowerCase()}::${(dPhone || "").trim()}`,
    [dNom, dPhone]
  );
  const dismissed = dismissedKey === currentKey;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!dNom || dNom.trim().length < 3) {
        setMatches([]);
        onMatchesChange?.([]);
        return;
      }
      try {
        const r = await checkDuplicates({ nom: dNom, telephone: dPhone, exclude_id: excludeId });
        if (cancelled) return;
        setMatches(r.matches || []);
        onMatchesChange?.(r.matches || []);
      } catch {
        if (!cancelled) {
          setMatches([]);
          onMatchesChange?.([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dNom, dPhone, excludeId]);

  if (!matches.length || dismissed) return null;

  return (
    <div
      data-testid="duplicate-warning"
      className="rounded-lg border-2 border-[#FF6200]/40 bg-[#FF6200]/8 dark:bg-[#FF6200]/15 p-4"
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 shrink-0 rounded-lg bg-[#FF6200]/20 flex items-center justify-center">
          <AlertTriangle className="w-4 h-4 text-[#FF6200]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#FF6200]">
                Doublon possible
              </p>
              <p className="text-sm font-semibold text-[#0A2540] dark:text-white mt-0.5">
                {matches.length} client{matches.length > 1 ? "s" : ""} existant
                {matches.length > 1 ? "s" : ""} ressemble{matches.length > 1 ? "nt" : ""} à votre
                saisie.
              </p>
            </div>
            <button
              type="button"
              data-testid="duplicate-warning-dismiss"
              onClick={() => setDismissedKey(currentKey)}
              className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 dark:text-white/50"
              aria-label="Masquer l'alerte"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <ul className="mt-3 space-y-1.5">
            {matches.map((m) => (
              <li
                key={m.client_id}
                data-testid={`duplicate-match-${m.reference}`}
                className="bg-white dark:bg-[#0A2540]/60 rounded-md px-3 py-2 border border-[#FF6200]/15 flex items-center gap-3 text-sm"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-[#0A2540] dark:text-white truncate">
                    {m.nom}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-white/60 truncate">
                    <span className="font-mono">{m.reference}</span>
                    {m.ville && <> · {m.ville}</>}
                    {m.telephone && (
                      <>
                        {" · "}
                        <Phone className="inline w-3 h-3 -mt-0.5" /> {m.telephone}
                      </>
                    )}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  {m.phone_match && (
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-[#C62828]/15 text-[#C62828] px-2 py-0.5 rounded">
                      Tel ✓
                    </span>
                  )}
                  <span className="text-[10px] uppercase tracking-wider text-[#FF6200] font-semibold">
                    {Math.round(m.similarity * 100)}%
                  </span>
                </div>
              </li>
            ))}
          </ul>

          <p className="text-[11px] text-gray-600 dark:text-white/60 mt-2 italic">
            {matches[0].reason}. Vérifiez avant de créer un nouveau client.
          </p>
        </div>
      </div>
    </div>
  );
}
