import { useEffect, useRef, useState } from "react";
import { X, Camera, AlertCircle } from "lucide-react";
import { BrowserMultiFormatReader } from "@zxing/browser";

/**
 * Bonus Sprint 5 — Scanner ISBN par caméra.
 * Utilise @zxing/browser pour décoder en live les codes-barres EAN-13/ISBN.
 *
 * Fallback manuel : champ texte + "Utiliser cet ISBN".
 *
 * Props:
 *  open: boolean
 *  onClose()
 *  onDetected(isbn: string)
 */
export default function IsbnScannerModal({ open, onClose, onDetected }) {
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const [error, setError] = useState(null);
  const [manualIsbn, setManualIsbn] = useState("");
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (!open) return;
    let reader;
    let stopped = false;

    (async () => {
      try {
        reader = new BrowserMultiFormatReader();
        // List cameras and prefer back camera if available
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        if (!devices || devices.length === 0) {
          throw new Error("Aucune caméra détectée");
        }
        const back = devices.find((d) => /back|rear|environment/i.test(d.label));
        const deviceId = (back || devices[devices.length - 1]).deviceId;

        const controls = await reader.decodeFromVideoDevice(
          deviceId,
          videoRef.current,
          (result, _err, ctl) => {
            if (stopped) return;
            if (result) {
              const txt = result.getText();
              if (/^\d{10,13}[Xx]?$/.test(txt)) {
                stopped = true;
                try { ctl.stop(); } catch (_) {}
                onDetected?.(txt);
              }
            }
          }
        );
        controlsRef.current = controls;
        setActive(true);
      } catch (e) {
        setError(
          e?.message?.includes("denied") || e?.name === "NotAllowedError"
            ? "Autorisation caméra refusée. Saisissez l'ISBN manuellement ci-dessous."
            : "Caméra indisponible. Saisissez l'ISBN manuellement."
        );
      }
    })();

    return () => {
      stopped = true;
      try {
        controlsRef.current?.stop();
      } catch (_) {}
      controlsRef.current = null;
      setActive(false);
    };
  }, [open, onDetected]);

  if (!open) return null;

  return (
    <div
      data-testid="isbn-scanner-modal"
      className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-3"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="bg-white dark:bg-[#0A2540] rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#FF6200]" />
            <h3 className="text-sm font-bold text-[#0A2540] dark:text-white">
              Scanner un code-barres ISBN
            </h3>
          </div>
          <button
            data-testid="isbn-scanner-close"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-white/60"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Camera viewport */}
          <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
            <video
              ref={videoRef}
              data-testid="isbn-scanner-video"
              className="w-full h-full object-cover"
              playsInline
              muted
            />
            {/* scan overlay */}
            <div
              aria-hidden
              className="absolute inset-x-8 inset-y-12 border-2 border-[#FF6200] rounded-lg shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"
            />
            {!active && !error && (
              <div className="absolute inset-0 flex items-center justify-center text-white/80 text-xs">
                Activation de la caméra…
              </div>
            )}
          </div>

          {error && (
            <div
              data-testid="isbn-scanner-error"
              className="flex items-start gap-2 text-xs text-[#C62828] bg-red-50 dark:bg-[#C62828]/10 p-3 rounded-lg"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Manual fallback */}
          <div className="pt-2 border-t border-gray-100 dark:border-white/10">
            <label className="block text-[10px] uppercase tracking-wider font-semibold text-[#0A2540]/70 dark:text-white/60 mb-1.5">
              Ou saisir l'ISBN manuellement
            </label>
            <div className="flex gap-2">
              <input
                data-testid="isbn-scanner-manual-input"
                type="text"
                value={manualIsbn}
                onChange={(e) => setManualIsbn(e.target.value.replace(/[^0-9Xx]/g, ""))}
                placeholder="978..."
                className="flex-1 px-3 py-2 text-sm rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-[#0A2540] dark:text-white"
              />
              <button
                data-testid="isbn-scanner-manual-submit"
                disabled={manualIsbn.length < 8}
                onClick={() => onDetected?.(manualIsbn)}
                className="px-4 py-2 rounded-lg bg-[#FF6200] hover:bg-[#E65800] disabled:opacity-40 text-white text-xs font-semibold"
              >
                Valider
              </button>
            </div>
          </div>

          <p className="text-[10px] text-gray-500 dark:text-white/40 text-center">
            Visez le code-barres au dos du livre — la détection est automatique.
          </p>
        </div>
      </div>
    </div>
  );
}
