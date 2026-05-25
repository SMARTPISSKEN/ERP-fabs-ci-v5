import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Pencil, PowerOff, BookOpen, Wallet, Package, Calendar, AlertCircle,
  FileText, History, ShoppingCart,
} from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import ProductFormDialog from "../components/products/ProductFormDialog";
import StockBadge from "../components/products/StockBadge";
import { CATEGORIES_MAP, getProduct, disableProduct } from "../services/produitsApi";
import { formatFCFA } from "../utils/format";
import { useAuth } from "../hooks/useAuth";

const WRITE_ROLES = new Set(["super_admin", "directeur_general", "directeur_commercial", "gestionnaire_stock", "responsable_magasinier"]);
const FINANCIAL_ROLES = new Set(["super_admin", "directeur_general", "comptable"]);

const TABS = [
  { key: "info",      label: "Informations",       icon: FileText },
  { key: "mouvements", label: "Mouvements stock",  icon: History },
  { key: "commandes", label: "Historique commandes", icon: ShoppingCart },
];

export default function ProduitDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { role } = useAuth();
  const canWrite = WRITE_ROLES.has(role);
  const seePrixAchat = FINANCIAL_ROLES.has(role);

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("info");
  const [edit, setEdit] = useState(false);

  const refresh = async () => {
    setLoading(true); setError(null);
    try { setProduct(await getProduct(id)); }
    catch (e) { setError(e?.response?.data?.detail || "Produit introuvable"); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [id]);

  const handleDisable = async () => {
    if (!window.confirm(`Désactiver le produit "${product.titre}" ?`)) return;
    try { setProduct(await disableProduct(product.product_id)); toast.success("Produit désactivé"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Échec"); }
  };

  if (loading) return <DashboardLayout><div className="text-sm text-gray-500 dark:text-white/50 p-8">Chargement…</div></DashboardLayout>;

  if (error || !product) {
    return (
      <DashboardLayout>
        <div className="bg-red-50 border border-[#C62828]/30 text-[#C62828] rounded-lg p-4 text-sm flex items-center gap-2 max-w-2xl">
          <AlertCircle className="w-4 h-4" /> {error || "Produit introuvable"}
          <button onClick={() => navigate("/produits")} className="ml-auto text-xs font-semibold underline">← Retour</button>
        </div>
      </DashboardLayout>
    );
  }

  const cat = CATEGORIES_MAP[product.categorie] || CATEGORIES_MAP.primaire;
  const marge = seePrixAchat && product.prix_achat != null
    ? product.prix_vente - product.prix_achat
    : null;

  return (
    <DashboardLayout>
      <div data-testid="produit-detail-page" className="max-w-6xl mx-auto">
        <button data-testid="produit-detail-back" onClick={() => navigate("/produits")}
          className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-white/50 hover:text-[#FF6200] transition-colors mb-4">
          <ArrowLeft className="w-3.5 h-3.5" /> Catalogue produits
        </button>

        {/* Header */}
        <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-6 shadow-sm">
          <div className="flex flex-wrap items-start gap-4 justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center flex-wrap gap-3">
                <span className="inline-flex items-center text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded"
                  style={{ background: cat.bg, color: cat.color }}>{cat.label}</span>
                <span className="font-mono text-xs text-gray-500 dark:text-white/50">{product.reference}</span>
                <StockBadge statut={product.statut_stock} stock_actuel={product.stock_actuel} stock_minimum={product.stock_minimum} />
                {!product.actif && (
                  <span className="text-[10px] uppercase tracking-wider bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-white/60 px-2 py-0.5 rounded">Désactivé</span>
                )}
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-[#0A2540] dark:text-white mt-2">{product.titre}</h1>
              <p className="text-sm text-gray-600 dark:text-white/70 mt-1">
                {[product.auteur, product.collection, product.niveau_scolaire].filter(Boolean).join(" · ")}
              </p>
              {product.isbn && (
                <p className="text-xs text-gray-500 dark:text-white/50 mt-1 font-mono">ISBN {product.isbn}</p>
              )}
            </div>
            {canWrite && product.actif && (
              <div className="flex gap-2">
                <button data-testid="produit-detail-edit" onClick={() => setEdit(true)}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-[#0A2540] dark:text-white bg-gray-100 dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/20">
                  <Pencil className="w-3.5 h-3.5" /> Modifier
                </button>
                <button data-testid="produit-detail-disable" onClick={handleDisable}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-[#C62828] bg-[#C62828]/10 hover:bg-[#C62828]/20">
                  <PowerOff className="w-3.5 h-3.5" /> Désactiver
                </button>
              </div>
            )}
          </div>

          {/* KPI */}
          <div className={`grid grid-cols-2 sm:grid-cols-${seePrixAchat ? 4 : 3} gap-4 mt-6 pt-6 border-t border-gray-100 dark:border-white/10`}>
            <KPI icon={Wallet} accent="#FF6200" label="Prix de vente" value={formatFCFA(product.prix_vente)} />
            {seePrixAchat && (
              <KPI icon={Wallet} accent="#0A2540" label="Prix d'achat" value={product.prix_achat != null ? formatFCFA(product.prix_achat) : "—"} />
            )}
            {seePrixAchat && marge != null && (
              <KPI icon={Wallet} accent="#2E7D32" label={`Marge unitaire`} value={formatFCFA(marge)} />
            )}
            <KPI icon={Package} accent={product.statut_stock === "rupture" ? "#C62828" : product.statut_stock === "alerte" ? "#FF6200" : "#2E7D32"}
              label="Stock actuel" value={`${product.stock_actuel} u.`} />
            <KPI icon={Calendar} accent="#7C5BC4" label="Créé le" value={new Date(product.created_at).toLocaleDateString("fr-FR")} />
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-6">
          <div data-testid="produit-detail-tabs" className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-white/10">
            {TABS.map(({ key, label, icon: Icon }) => {
              const active = key === tab;
              return (
                <button key={key} data-testid={`produit-detail-tab-${key}`} onClick={() => setTab(key)}
                  className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
                    active ? "border-[#FF6200] text-[#FF6200]" : "border-transparent text-gray-500 dark:text-white/60 hover:text-[#0A2540] dark:hover:text-white"
                  }`}>
                  <Icon className="w-3.5 h-3.5" /> {label}
                </button>
              );
            })}
          </div>

          <div className="mt-5">
            {tab === "info" && (
              <div data-testid="produit-detail-info" className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-6 shadow-sm">
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                  {[
                    ["Référence",       product.reference],
                    ["Titre",           product.titre],
                    ["Auteur",          product.auteur || "—"],
                    ["Collection",      product.collection || "—"],
                    ["Catégorie",       cat.label],
                    ["Niveau scolaire", product.niveau_scolaire || "—"],
                    ["ISBN",            product.isbn || "—"],
                    ["Prix de vente",   formatFCFA(product.prix_vente)],
                    ...(seePrixAchat ? [["Prix d'achat", product.prix_achat != null ? formatFCFA(product.prix_achat) : "—"]] : []),
                    ["Stock actuel",    `${product.stock_actuel} unité${product.stock_actuel > 1 ? "s" : ""}`],
                    ["Seuil alerte",    `${product.stock_minimum} unités`],
                    ["Créé le",         new Date(product.created_at).toLocaleString("fr-FR")],
                    ["Mis à jour",      new Date(product.updated_at).toLocaleString("fr-FR")],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 dark:text-white/50">{k}</dt>
                      <dd className="text-sm text-[#0A2540] dark:text-white mt-1 break-words">{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
            {tab !== "info" && (
              <div data-testid={`produit-detail-empty-${tab}`} className="bg-white dark:bg-white/5 rounded-xl border border-dashed border-gray-200 dark:border-white/10 p-10 text-center">
                <p className="text-[11px] uppercase tracking-[0.2em] text-[#FF6200] font-semibold">Bientôt</p>
                <p className="text-sm text-gray-600 dark:text-white/60 mt-2">
                  Cet onglet sera alimenté quand les modules {tab === "mouvements" ? "Stock (Sprint 9)" : "Commandes (Sprint 6)"} seront livrés.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <ProductFormDialog open={edit} onClose={() => setEdit(false)} product={product}
        onSaved={(saved) => { setProduct(saved); setEdit(false); }} />
    </DashboardLayout>
  );
}

function KPI({ icon: Icon, accent, label, value }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${accent}18` }}>
        <Icon className="w-5 h-5" style={{ color: accent }} />
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-white/50">{label}</p>
        <p className="text-sm font-bold text-[#0A2540] dark:text-white mt-0.5 whitespace-nowrap">{value}</p>
      </div>
    </div>
  );
}
