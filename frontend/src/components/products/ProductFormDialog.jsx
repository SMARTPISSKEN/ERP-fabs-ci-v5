import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, X, Save, ScanLine, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { CATEGORIES, createProduct, updateProduct, lookupIsbn } from "../../services/produitsApi";
// import IsbnScannerModal from "./IsbnScannerModal"; // Temporarily disabled due to @zxing/browser dependency
import { useAuth } from "../../hooks/useAuth";

const FINANCIAL_ROLES = new Set(["super_admin", "directeur_general", "comptable"]);

const Schema = z.object({
  titre: z.string().min(2, "Titre trop court").max(200),
  auteur: z.string().max(120).optional().or(z.literal("")),
  collection: z.string().max(120).optional().or(z.literal("")),
  categorie: z.enum(["maternelle", "primaire", "premier_cycle", "second_cycle", "litterature"]),
  niveau_scolaire: z.string().max(80).optional().or(z.literal("")),
  isbn: z.string().max(20).optional().or(z.literal("")),
  prix_achat: z.coerce.number().min(0).default(0),
  prix_vente: z.coerce.number().gt(0, "Doit être > 0"),
  stock_actuel: z.coerce.number().int().min(0).default(0),
  stock_minimum: z.coerce.number().int().min(0).default(10),
});

export default function ProductFormDialog({ open, onClose, onSaved, product }) {
  const editing = Boolean(product);
  const { role } = useAuth();
  const canSeePrixAchat = FINANCIAL_ROLES.has(role);

  const [submitting, setSubmitting] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [looking, setLooking] = useState(false);

  const {
    register, handleSubmit, reset, setValue, watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(Schema),
    defaultValues: {
      titre: "", auteur: "", collection: "",
      categorie: "primaire", niveau_scolaire: "",
      isbn: "", prix_achat: 0, prix_vente: 1000,
      stock_actuel: 50, stock_minimum: 10,
    },
  });

  useEffect(() => {
    if (!open) return;
    reset({
      titre: product?.titre || "",
      auteur: product?.auteur || "",
      collection: product?.collection || "",
      categorie: product?.categorie || "primaire",
      niveau_scolaire: product?.niveau_scolaire || "",
      isbn: product?.isbn || "",
      prix_achat: product?.prix_achat ?? 0,
      prix_vente: product?.prix_vente || 1000,
      stock_actuel: product?.stock_actuel ?? 50,
      stock_minimum: product?.stock_minimum ?? 10,
    });
  }, [open, product, reset]);

  if (!open) return null;

  const isbnLive = watch("isbn");

  const handleIsbnDetected = async (isbn) => {
    setScannerOpen(false);
    setValue("isbn", isbn);
    await handleLookup(isbn);
  };

  const handleLookup = async (forceIsbn) => {
    const code = (forceIsbn || isbnLive || "").trim();
    if (!code || code.length < 8) {
      toast.error("Saisissez d'abord un ISBN valide");
      return;
    }
    setLooking(true);
    try {
      const r = await lookupIsbn(code);
      if (!r.found) {
        toast.info("ISBN non trouvé sur Google Books", { description: "Saisissez les informations manuellement." });
        return;
      }
      let updates = 0;
      if (r.titre && !watch("titre")) { setValue("titre", r.titre); updates++; }
      if (r.auteur && !watch("auteur")) { setValue("auteur", r.auteur); updates++; }
      if (r.collection && !watch("collection")) { setValue("collection", r.collection); updates++; }
      if (r.categorie && !watch("categorie")) { setValue("categorie", r.categorie); updates++; }
      toast.success(`ISBN trouvé — ${updates} champ${updates > 1 ? "s" : ""} pré-rempli${updates > 1 ? "s" : ""}`, {
        icon: "✨",
        description: r.titre,
      });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Recherche ISBN échouée");
    } finally {
      setLooking(false);
    }
  };

  const submit = async (values) => {
    setSubmitting(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(values).map(([k, v]) => [k, v === "" ? null : v])
      );
      if (editing) {
        const saved = await updateProduct(product.product_id, payload);
        toast.success(`Produit ${saved.reference} mis à jour`);
        onSaved?.(saved);
      } else {
        const saved = await createProduct(payload);
        toast.success(`Produit ${saved.reference} créé`);
        onSaved?.(saved);
      }
      onClose?.();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Échec de l'enregistrement";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div
        data-testid="product-form-dialog"
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) onClose?.();
        }}
      >
        <div className="bg-white dark:bg-[#0A2540] w-full sm:max-w-3xl sm:rounded-2xl rounded-t-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
          <div className="sticky top-0 bg-white dark:bg-[#0A2540] border-b border-gray-100 dark:border-white/10 px-6 py-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-[#FF6200] font-semibold">
                {editing ? "Modification" : "Nouveau produit"}
              </p>
              <h2 className="text-xl font-bold text-[#0A2540] dark:text-white tracking-tight mt-0.5">
                {editing ? product.titre : "Création d'un livre"}
              </h2>
            </div>
            <button
              data-testid="product-form-close"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-white/60"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit(submit)} className="px-6 py-5 space-y-5" noValidate>
            {/* ISBN with scanner & lookup BONUS */}
            <div className="bg-[#FF6200]/5 dark:bg-[#FF6200]/10 border border-[#FF6200]/20 rounded-xl p-4">
              <label className="block text-[10px] uppercase tracking-wider font-semibold text-[#FF6200] mb-2">
                <Sparkles className="w-3 h-3 inline mr-1" /> Scan ISBN — Auto-complétion
              </label>
              <div className="flex gap-2 flex-wrap sm:flex-nowrap">
                <input
                  data-testid="product-form-isbn"
                  {...register("isbn")}
                  placeholder="ISBN (978...)"
                  className="flex-1 min-w-0 px-3 py-2.5 text-sm rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 text-[#0A2540] dark:text-white font-mono"
                />
                <button
                  type="button"
                  data-testid="product-form-scan-btn"
                  onClick={() => setScannerOpen(true)}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg bg-[#0A2540] hover:bg-[#091a30] text-white text-xs font-semibold"
                  title="Scanner avec la caméra"
                >
                  <ScanLine className="w-3.5 h-3.5" />
                  Scanner
                </button>
                <button
                  type="button"
                  data-testid="product-form-lookup-btn"
                  disabled={looking}
                  onClick={() => handleLookup()}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg bg-[#FF6200] hover:bg-[#E65800] disabled:opacity-50 text-white text-xs font-semibold"
                >
                  {looking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  Rechercher
                </button>
              </div>
              <p className="text-[10px] text-[#0A2540]/60 dark:text-white/40 mt-2">
                Scanne le code-barres au dos du livre OU saisis l'ISBN, puis clique « Rechercher » pour pré-remplir le titre, l'auteur et la collection depuis Google Books.
              </p>
            </div>

            {/* Titre + Catégorie */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <Label>Titre *</Label>
                <input data-testid="product-form-titre" {...register("titre")} className={inputCls(errors.titre)} />
                {errors.titre && <Err msg={errors.titre.message} />}
              </div>
              <div>
                <Label>Catégorie *</Label>
                <select data-testid="product-form-categorie" {...register("categorie")} className={inputCls(errors.categorie)}>
                  {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
            </div>

            {/* Auteur + Collection */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label>Auteur</Label>
                <input data-testid="product-form-auteur" {...register("auteur")} className={inputCls(errors.auteur)} />
              </div>
              <div>
                <Label>Collection / Éditeur</Label>
                <input data-testid="product-form-collection" {...register("collection")} className={inputCls(errors.collection)} />
              </div>
            </div>

            <div>
              <Label>Niveau scolaire</Label>
              <input data-testid="product-form-niveau" {...register("niveau_scolaire")} placeholder="CP1, 6e, Terminale..." className={inputCls(errors.niveau_scolaire)} />
            </div>

            {/* Prices */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {canSeePrixAchat && (
                <div>
                  <Label>Prix d'achat (FCFA) <span className="text-[9px] text-gray-400">— interne</span></Label>
                  <input type="number" min={0} step={100} data-testid="product-form-prix-achat" {...register("prix_achat")} className={inputCls(errors.prix_achat)} />
                </div>
              )}
              <div className={canSeePrixAchat ? "" : "sm:col-span-2"}>
                <Label>Prix de vente (FCFA) *</Label>
                <input type="number" min={0} step={100} data-testid="product-form-prix-vente" {...register("prix_vente")} className={inputCls(errors.prix_vente)} />
                {errors.prix_vente && <Err msg={errors.prix_vente.message} />}
              </div>
            </div>

            {/* Stock */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label>Stock actuel</Label>
                <input type="number" min={0} data-testid="product-form-stock-actuel" {...register("stock_actuel")} className={inputCls(errors.stock_actuel)} />
              </div>
              <div>
                <Label>Stock minimum (seuil alerte)</Label>
                <input type="number" min={0} data-testid="product-form-stock-minimum" {...register("stock_minimum")} className={inputCls(errors.stock_minimum)} />
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 pt-3 border-t border-gray-100 dark:border-white/10">
              <button type="button" data-testid="product-form-cancel" onClick={onClose}
                className="px-4 py-2.5 rounded-lg text-sm font-semibold text-[#0A2540] dark:text-white hover:bg-gray-100 dark:hover:bg-white/10">
                Annuler
              </button>
              <button type="submit" data-testid="product-form-submit" disabled={submitting}
                className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#FF6200] hover:bg-[#E65800] disabled:opacity-60 text-white text-sm font-semibold shadow-md hover:shadow-lg transition">
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {editing ? "Enregistrer" : "Créer le produit"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* IsbnScannerModal temporarily disabled due to @zxing/browser dependency */}
      {/* <IsbnScannerModal
        open={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onDetected={handleIsbnDetected}
      /> */}
    </>
  );
}

const Label = ({ children }) => (
  <label className="block text-[11px] uppercase tracking-wider font-semibold text-[#0A2540]/70 dark:text-white/60 mb-1.5">
    {children}
  </label>
);
const Err = ({ msg }) => <p className="text-[11px] text-[#C62828] mt-1">{msg}</p>;
const inputCls = (hasErr) =>
  `w-full px-3 py-2.5 text-sm rounded-lg bg-white dark:bg-white/5 border ${
    hasErr ? "border-[#C62828]" : "border-gray-200 dark:border-white/10"
  } text-[#0A2540] dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200]`;
