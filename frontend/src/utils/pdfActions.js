/**
 * Utilitaires pour le téléchargement, l'impression et le partage WhatsApp des PDFs.
 * Les endpoints PDF requièrent une authentification Bearer, donc on fetch le blob
 * puis on opère sur le blob URL (impression, téléchargement).
 */
import { toast } from "sonner";
import { tokenStore } from "../hooks/useAuth";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

const fetchPdfBlob = async (path) => {
  const token = tokenStore.get();
  const response = await fetch(`${API}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    let detail = "Erreur génération PDF";
    try {
      const json = await response.json();
      if (json?.detail) detail = json.detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  return await response.blob();
};

export const downloadPdf = async (path, filename) => {
  try {
    const blob = await fetchPdfBlob(path);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "document.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    toast.success("PDF téléchargé");
  } catch (e) {
    toast.error(e.message || "Erreur lors du téléchargement");
  }
};

export const printPdf = async (path) => {
  try {
    const blob = await fetchPdfBlob(path);
    const url = window.URL.createObjectURL(blob);
    const win = window.open(url, "_blank");
    if (!win) {
      toast.error("Veuillez autoriser les pop-ups pour imprimer");
      return;
    }
    win.addEventListener("load", () => {
      try {
        win.focus();
        win.print();
      } catch (_) { /* ignore */ }
    });
    toast.success("Aperçu d'impression ouvert");
  } catch (e) {
    toast.error(e.message || "Erreur lors de l'impression");
  }
};

export const previewPdf = async (path) => {
  try {
    const blob = await fetchPdfBlob(path);
    const url = window.URL.createObjectURL(blob);
    const win = window.open(url, "_blank");
    if (!win) {
      toast.error("Veuillez autoriser les pop-ups pour l'aperçu");
    }
  } catch (e) {
    toast.error(e.message || "Erreur lors de l'aperçu");
  }
};

/**
 * Partage via WhatsApp en envoyant un message texte récapitulatif.
 * L'utilisateur attachera le PDF manuellement après téléchargement.
 * @param {object} opts
 * @param {string} opts.type - "Facture", "Commande", "Bon de livraison"
 * @param {string} opts.reference
 * @param {string} [opts.clientNom]
 * @param {number} [opts.montant]
 * @param {string} [opts.telephone] - Numéro destinataire au format international sans + (ex: 22507XXXXXXXX)
 */
export const shareWhatsApp = ({ type, reference, clientNom, montant, telephone }) => {
  const formatFcfa = (m) =>
    new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
      .format(m || 0) + " FCFA";

  const lines = [
    `*EDITIONS FABS-CI*`,
    `${type} : *${reference}*`,
  ];
  if (clientNom) lines.push(`Client : ${clientNom}`);
  if (montant != null) lines.push(`Montant : ${formatFcfa(montant)}`);
  lines.push("");
  lines.push("Veuillez trouver le document en pièce jointe.");
  lines.push("Cordialement.");

  const text = encodeURIComponent(lines.join("\n"));
  const phone = (telephone || "").replace(/[^0-9]/g, "");
  const url = phone
    ? `https://wa.me/${phone}?text=${text}`
    : `https://wa.me/?text=${text}`;
  window.open(url, "_blank");
};
