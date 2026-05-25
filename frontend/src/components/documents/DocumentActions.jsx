/**
 * DocumentActions — boutons Aperçu / Imprimer / Envoyer WhatsApp
 *
 * Usage :
 *   <DocumentActions
 *     pdfUrl="/api/factures/<id>/pdf"
 *     filename="FABS-FC-26-27-0001.pdf"
 *     phone="+225 07 ..."  // optionnel — pré-rempli pour WhatsApp
 *     message="Bonjour, voici votre facture FABS-FC-26-27-0001"
 *   />
 *
 * Les boutons :
 *  - Aperçu  → ouvre le PDF dans un nouvel onglet (inline)
 *  - Imprimer → ouvre le PDF dans un iframe caché et déclenche window.print()
 *  - WhatsApp → wa.me/<num>?text=<msg> + lien vers le PDF
 */
import { useRef } from "react";
import { Eye, Printer, MessageCircle } from "lucide-react";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { tokenStore } from "../../hooks/useAuth";

export default function DocumentActions({
  pdfUrl,
  filename,
  phone,
  message,
  testIdPrefix = "doc",
}) {
  const iframeRef = useRef(null);

  const openPdfBlob = async (action) => {
    try {
      const token = tokenStore.get();
      const res = await fetch(pdfUrl, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (action === "preview") {
        window.open(url, "_blank", "noopener,noreferrer");
      } else if (action === "print") {
        if (iframeRef.current) {
          iframeRef.current.src = url;
          iframeRef.current.onload = () => {
            try {
              iframeRef.current.contentWindow.focus();
              iframeRef.current.contentWindow.print();
            } catch (e) {
              window.open(url, "_blank");
            }
          };
        } else {
          const w = window.open(url, "_blank");
          if (w) setTimeout(() => w.print(), 800);
        }
      } else if (action === "download") {
        const a = document.createElement("a");
        a.href = url;
        a.download = filename || "document.pdf";
        a.click();
      }
    } catch (e) {
      toast.error("Impossible de charger le PDF");
    }
  };

  const handleWhatsApp = () => {
    const cleanPhone = (phone || "").replace(/\D/g, "");
    const num = cleanPhone
      ? cleanPhone.startsWith("225") ? cleanPhone : `225${cleanPhone}`
      : "";
    const text = encodeURIComponent(
      message ||
        `Bonjour, vous trouverez ci-joint votre document FABS-CI : ${filename || ""}`
    );
    const url = num
      ? `https://wa.me/${num}?text=${text}`
      : `https://wa.me/?text=${text}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="flex flex-wrap gap-2 items-center" data-testid={`${testIdPrefix}-actions`}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => openPdfBlob("preview")}
        data-testid={`${testIdPrefix}-preview-btn`}
      >
        <Eye className="h-4 w-4 mr-2" />
        Aperçu
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => openPdfBlob("print")}
        data-testid={`${testIdPrefix}-print-btn`}
      >
        <Printer className="h-4 w-4 mr-2" />
        Imprimer
      </Button>
      <Button
        size="sm"
        onClick={handleWhatsApp}
        className="bg-[#25D366] hover:bg-[#1EBE5D] text-white"
        data-testid={`${testIdPrefix}-whatsapp-btn`}
      >
        <MessageCircle className="h-4 w-4 mr-2" />
        WhatsApp
      </Button>
      <iframe
        ref={iframeRef}
        title="print-frame"
        style={{ display: "none" }}
      />
    </div>
  );
}
