import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Plus, Pencil, PowerOff, ChevronLeft, ChevronRight, AlertCircle, RotateCw,
} from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import ProductFormDialog from "../components/products/ProductFormDialog";
import StockBadge from "../components/products/StockBadge";
import { CATEGORIES, CATEGORIES_MAP, listProducts, disableProduct } from "../services/produitsApi";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { formatFCFA } from "../utils/format";
import { useAuth } from "../hooks/useAuth";

const WRITE_ROLES = new Set([
  "super_admin", "directeur_general", "directeur_commercial",
  "gestionnaire_stock", "responsable_magasinier",
]);
const FINANCIAL_ROLES = new Set(["super_admin", "directeur_general", "comptable"]);

export default function Produits() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const canWrite = WRITE_ROLES.has(role);
  const seePrixAchat = FINANCIAL_ROLES.has(role);

  const [q, setQ] = useState("");
  const [categorie, setCategorie] = useState("");
  const [niveau, setNiveau] = useState("");
  const [statutStock, setStatutStock] = useState("");
  const [actif, setActif] = useState("true");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const dq = useDebouncedValue(q, 300);
  const dniveau = useDebouncedValue(niveau, 300);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await listProducts({
        q: dq || undefined,
        categorie: categorie || undefined,
        niveau_scolaire: dniveau || undefined,
        statut_stock: statutStock || undefined,
        actif: actif === "" ? undefined : actif === "true",
        page,
        page_size: PAGE_SIZE,
      });
      setData(r);
    } catch (e) {
      setError(e?.response?.data?.detail || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [dq, categorie, dniveau, statutStock, actif, page]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setPage(1); }, [dq, categorie, dniveau, statutStock, actif]);

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  const handleDisable = async (product) => {
    if (!window.confirm(`Désactiver le produit "${product.titre}" ?`)) return;
    try {
      await disableProduct(product.product_id);
      toast.success(`${product.titre} désactivé`);
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Échec de la désactivation");
    }
  };

  return (
    <DashboardLayout>
      <div data-testid="produits-page" className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between mb-6 gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#FF6200] font-semibold">
              Module Produits
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-[#0A2540] dark:text-white mt-1">
              Catalogue livres
            </h1>
            <p className="text-sm text-gray-600 dark:text-white/60 mt-1">
              {data.total} produit{data.total > 1 ? "s" : ""} dans le catalogue.
            </p>
          </div>
          {canWrite && (
            <button
              data-testid="produits-new-btn"
              onClick={() => { setEditing(null); setDialogOpen(true); }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#FF6200] hover:bg-[#E65800] text-white text-sm font-semibold shadow-md hover:shadow-lg transition"
            >
              <Plus className="w-4 h-4" />
              Nouveau produit
            </button>
          )}
        </div>

        {/* Filters */}
        <div data-testid="produits-filters" className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-4 mb-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="relative lg:col-span-2">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              data-testid="produits-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Titre, référence, ISBN, auteur..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200] text-[#0A2540] dark:text-white"
            />
          </div>
          <select data-testid="produits-filter-categorie" value={categorie} onChange={(e) => setCategorie(e.target.value)}
            className="text-sm rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-3 py-2 text-[#0A2540] dark:text-white">
            <option value="">Toutes catégories</option>
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <input data-testid="produits-filter-niveau" value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="Niveau..."
            className="text-sm rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-3 py-2 text-[#0A2540] dark:text-white" />
          <select data-testid="produits-filter-stock" value={statutStock} onChange={(e) => setStatutStock(e.target.value)}
            className="text-sm rounded-lg border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-3 py-2 text-[#0A2540] dark:text-white">
            <option value="">Tous stocks</option>
            <option value="rupture">En rupture</option>
            <option value="alerte">Alerte stock</option>
            <option value="ok">Stock OK</option>
          </select>
        </div>

        {error && (
          <div data-testid="produits-error" className="bg-red-50 border border-[#C62828]/30 text-[#C62828] rounded-lg p-4 text-sm mb-5 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
            <button onClick={fetchData} className="ml-auto text-xs font-semibold underline">
              <RotateCw className="w-3 h-3 inline mr-1" /> Réessayer
            </button>
          </div>
        )}

        {/* Table */}
        <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-white/5 text-[10px] uppercase tracking-wider text-[#0A2540]/70 dark:text-white/60">
                  <th className="text-left px-4 py-3 font-semibold">Référence</th>
                  <th className="text-left px-4 py-3 font-semibold">Titre</th>
                  <th className="text-left px-4 py-3 font-semibold">Catégorie</th>
                  <th className="text-left px-4 py-3 font-semibold">Niveau</th>
                  {seePrixAchat && <th className="text-right px-4 py-3 font-semibold">Prix achat</th>}
                  <th className="text-right px-4 py-3 font-semibold">Prix vente</th>
                  <th className="text-right px-4 py-3 font-semibold">Stock</th>
                  <th className="text-center px-4 py-3 font-semibold">Statut</th>
                  <th className="text-right px-4 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={seePrixAchat ? 9 : 8} className="px-4 py-10 text-center text-gray-500 dark:text-white/50">Chargement…</td></tr>
                )}
                {!loading && data.items.length === 0 && (
                  <tr><td colSpan={seePrixAchat ? 9 : 8} className="px-4 py-10 text-center text-gray-500 dark:text-white/50">Aucun produit trouvé.</td></tr>
                )}
                {!loading && data.items.map((p) => {
                  const cat = CATEGORIES_MAP[p.categorie] || CATEGORIES[0];
                  return (
                    <tr
                      key={p.product_id}
                      data-testid={`produits-row-${p.reference}`}
                      className="border-t border-gray-100 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer"
                      onClick={() => navigate(`/produits/${p.product_id}`)}
                    >
                      <td className="px-4 py-3 font-mono text-xs text-[#0A2540] dark:text-white/90 whitespace-nowrap">{p.reference}</td>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-[#0A2540] dark:text-white">{p.titre}</p>
                        {p.auteur && <p className="text-[11px] text-gray-500 dark:text-white/50">{p.auteur}</p>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded"
                          style={{ background: cat.bg, color: cat.color }}>
                          {cat.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-700 dark:text-white/80 whitespace-nowrap">{p.niveau_scolaire || "—"}</td>
                      {seePrixAchat && (
                        <td className="px-4 py-3 text-right text-gray-700 dark:text-white/70 whitespace-nowrap text-xs">
                          {p.prix_achat != null ? formatFCFA(p.prix_achat) : "—"}
                        </td>
                      )}
                      <td className="px-4 py-3 text-right font-semibold text-[#0A2540] dark:text-white whitespace-nowrap">
                        {formatFCFA(p.prix_vente)}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <span className="font-semibold text-[#0A2540] dark:text-white">{p.stock_actuel}</span>
                        <span className="text-[10px] text-gray-400 dark:text-white/40"> / {p.stock_minimum} min</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StockBadge statut={p.statut_stock} stock_actuel={p.stock_actuel} stock_minimum={p.stock_minimum} />
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        {canWrite && p.actif && (
                          <div className="inline-flex items-center gap-1">
                            <button data-testid={`produits-edit-${p.reference}`} onClick={() => { setEditing(p); setDialogOpen(true); }}
                              className="p-1.5 rounded hover:bg-[#FF6200]/10 text-[#0A2540] dark:text-white/80" title="Modifier">
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button data-testid={`produits-disable-${p.reference}`} onClick={() => handleDisable(p)}
                              className="p-1.5 rounded hover:bg-[#C62828]/10 text-[#C62828]" title="Désactiver">
                              <PowerOff className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {data.total > PAGE_SIZE && (
            <div data-testid="produits-pagination" className="border-t border-gray-100 dark:border-white/10 px-4 py-3 flex items-center justify-between text-xs text-gray-600 dark:text-white/60">
              <span>Page {page} / {totalPages} ({data.total} résultat{data.total > 1 ? "s" : ""})</span>
              <div className="flex gap-2">
                <button data-testid="produits-prev-page" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-white/5">
                  <ChevronLeft className="w-3 h-3" /> Préc.
                </button>
                <button data-testid="produits-next-page" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-white/5">
                  Suiv. <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <ProductFormDialog open={dialogOpen} onClose={() => setDialogOpen(false)} product={editing} onSaved={() => fetchData()} />
    </DashboardLayout>
  );
}
