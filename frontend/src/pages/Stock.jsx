/**
 * Page Stock — Sprint 9
 * Mouvements de stock : entrée, sortie, ajustement, retour, spécimen gratuit.
 * Règle Sprint 14 : seuls les rôles `gestionnaire_stock`, `responsable_magasinier`,
 * `super_admin` et `directeur_general` peuvent créer un mouvement.
 */
import React, { useState, useEffect } from "react";
import { Plus, Filter, Package, ArrowDown, ArrowUp, RefreshCw, Gift } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";

import { getMouvements, createMouvement } from "../services/stockApi";
import { listProducts } from "../services/produitsApi";
import { useAuth } from "../hooks/useAuth";

const TYPE_CONFIG = {
  entree: { label: "Entrée", color: "bg-green-600", Icon: ArrowDown },
  sortie: { label: "Sortie", color: "bg-red-600", Icon: ArrowUp },
  ajustement: { label: "Ajustement", color: "bg-blue-600", Icon: RefreshCw },
  retour: { label: "Retour", color: "bg-orange-500", Icon: ArrowDown },
  specimen_gratuit: { label: "Spécimen gratuit", color: "bg-purple-600", Icon: Gift },
};

const formatDate = (s) => (s ? new Date(s).toLocaleDateString("fr-FR") : "-");

export default function Stock() {
  const { user } = useAuth();
  const canWrite = user && ["super_admin", "directeur_general", "gestionnaire_stock", "responsable_magasinier"].includes(user.role);

  const [mouvements, setMouvements] = useState([]);
  const [produits, setProduits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ produit_id: "", type_mouvement: "" });
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    listProducts({ actif: true, limit: 200 }).then((d) => setProduits(d.items || d || [])).catch(() => {});
    fetchMouvements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchMouvements = async () => {
    setLoading(true);
    try {
      const data = await getMouvements({ ...filters, limit: 100 });
      setMouvements(data);
    } catch (e) {
      toast.error("Erreur chargement mouvements");
    } finally {
      setLoading(false);
    }
  };

  const stats = mouvements.reduce(
    (acc, m) => {
      if (m.type_mouvement === "entree") acc.entrees += m.quantite;
      else if (m.type_mouvement === "sortie") acc.sorties += m.quantite;
      else if (m.type_mouvement === "specimen_gratuit") acc.specimens += m.quantite;
      return acc;
    },
    { entrees: 0, sorties: 0, specimens: 0 }
  );

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="stock-page">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Stock & Mouvements</h1>
            <p className="text-gray-600 dark:text-white/60 mt-1">
              Historique des entrées, sorties, ajustements et spécimens gratuits
            </p>
          </div>
          {canWrite && (
            <Button onClick={() => setShowForm(true)} className="bg-[#FF6200] hover:bg-[#E55900] text-white" data-testid="btn-nouveau-mouvement">
              <Plus className="h-4 w-4 mr-2" /> Nouveau mouvement
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total entrées</CardDescription>
              <CardTitle className="text-2xl text-green-600">{stats.entrees}</CardTitle>
            </CardHeader>
            <CardContent><ArrowDown className="h-4 w-4 text-green-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total sorties</CardDescription>
              <CardTitle className="text-2xl text-red-600">{stats.sorties}</CardTitle>
            </CardHeader>
            <CardContent><ArrowUp className="h-4 w-4 text-red-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Spécimens gratuits</CardDescription>
              <CardTitle className="text-2xl text-purple-600">{stats.specimens}</CardTitle>
            </CardHeader>
            <CardContent><Gift className="h-4 w-4 text-purple-500" /></CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center"><Filter className="h-5 w-5 mr-2" /> Filtres</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Produit</Label>
                <Select value={filters.produit_id || "all"} onValueChange={(v) => setFilters({ ...filters, produit_id: v === "all" ? "" : v })}>
                  <SelectTrigger data-testid="filter-produit"><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {produits.map((p) => (
                      <SelectItem key={p.product_id} value={p.product_id}>{p.titre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Type</Label>
                <Select value={filters.type_mouvement || "all"} onValueChange={(v) => setFilters({ ...filters, type_mouvement: v === "all" ? "" : v })}>
                  <SelectTrigger data-testid="filter-type"><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {Object.entries(TYPE_CONFIG).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button onClick={fetchMouvements} data-testid="btn-appliquer">Appliquer</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Historique des mouvements</CardTitle>
            <CardDescription>{mouvements.length} mouvement(s)</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
            ) : mouvements.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Package className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                Aucun mouvement
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left">
                      <th className="pb-3 font-semibold">Date</th>
                      <th className="pb-3 font-semibold">Produit</th>
                      <th className="pb-3 font-semibold">Type</th>
                      <th className="pb-3 font-semibold text-right">Quantité</th>
                      <th className="pb-3 font-semibold text-right">Stock avant</th>
                      <th className="pb-3 font-semibold text-right">Stock après</th>
                      <th className="pb-3 font-semibold">Motif</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mouvements.map((m) => {
                      const cfg = TYPE_CONFIG[m.type_mouvement] || { label: m.type_mouvement, color: "bg-gray-500" };
                      return (
                        <tr key={m.mouvement_id} className="border-b hover:bg-gray-50 dark:hover:bg-white/5" data-testid={`row-mvt-${m.mouvement_id}`}>
                          <td className="py-3 text-sm">{formatDate(m.created_at)}</td>
                          <td className="py-3">
                            <div className="font-mono text-xs text-gray-500">{m.produit_reference}</div>
                            <div className="text-sm">{m.produit_titre || m.produit_id}</div>
                          </td>
                          <td className="py-3"><Badge className={`${cfg.color} text-white`}>{cfg.label}</Badge></td>
                          <td className="py-3 text-right font-semibold">{m.quantite}</td>
                          <td className="py-3 text-right text-gray-500">{m.stock_avant}</td>
                          <td className="py-3 text-right font-bold text-[#FF6200]">{m.stock_apres}</td>
                          <td className="py-3 text-sm text-gray-600">{m.motif || "-"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <MouvementFormDialog
          open={showForm}
          onOpenChange={setShowForm}
          produits={produits}
          userRole={user?.role}
          onCreated={() => { setShowForm(false); fetchMouvements(); }}
        />
      </div>
    </DashboardLayout>
  );
}

function MouvementFormDialog({ open, onOpenChange, produits, userRole, onCreated }) {
  // Spécimen gratuit : exclusif au gestionnaire_stock / responsable_magasinier / super_admin / DG.
  const allTypes = Object.entries(TYPE_CONFIG);
  const [form, setForm] = useState({
    produit_id: "",
    type_mouvement: "entree",
    quantite: "",
    motif: "",
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.produit_id || !form.quantite) {
      toast.error("Produit et quantité obligatoires");
      return;
    }
    try {
      setSaving(true);
      await createMouvement({
        produit_id: form.produit_id,
        type_mouvement: form.type_mouvement,
        quantite: parseInt(form.quantite, 10),
        motif: form.motif || null,
      });
      toast.success("Mouvement enregistré");
      setForm({ produit_id: "", type_mouvement: "entree", quantite: "", motif: "" });
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur enregistrement");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="dialog-mouvement">
        <DialogHeader>
          <DialogTitle>Nouveau mouvement de stock</DialogTitle>
          <DialogDescription>Enregistrer une entrée, sortie ou ajustement</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Produit *</Label>
            <Select value={form.produit_id} onValueChange={(v) => setForm({ ...form, produit_id: v })}>
              <SelectTrigger data-testid="form-produit"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
              <SelectContent>
                {produits.map((p) => (
                  <SelectItem key={p.product_id} value={p.product_id}>
                    {p.titre} (stock: {p.stock_actuel || 0})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Type *</Label>
              <Select value={form.type_mouvement} onValueChange={(v) => setForm({ ...form, type_mouvement: v })}>
                <SelectTrigger data-testid="form-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {allTypes.map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.type_mouvement === "specimen_gratuit" && (
                <p className="text-[11px] text-purple-600 mt-1">
                  Sortie sans facturation — suivi spécimens gratuits.
                </p>
              )}
            </div>
            <div>
              <Label>Quantité *</Label>
              <Input
                type="number"
                min="1"
                value={form.quantite}
                onChange={(e) => setForm({ ...form, quantite: e.target.value })}
                data-testid="form-quantite"
              />
            </div>
          </div>
          <div>
            <Label>Motif</Label>
            <Textarea
              rows={2}
              placeholder="Raison du mouvement..."
              value={form.motif}
              onChange={(e) => setForm({ ...form, motif: e.target.value })}
              data-testid="form-motif"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-mouvement">
            {saving ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
