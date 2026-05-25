/**
 * Page Paiements — Sprint 8
 * Liste, filtres, création des règlements (FABS-REG-2026-XXXX)
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Filter, CreditCard, Wallet, ArrowLeftRight } from "lucide-react";
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

import { getPaiements, createPaiement } from "../services/paiementsApi";
import { getFactures } from "../services/facturesApi";
import { listClients } from "../services/clientsApi";
import { useAuth } from "../hooks/useAuth";

const MODES = {
  especes: { label: "Espèces", color: "bg-green-600" },
  cheque: { label: "Chèque", color: "bg-blue-600" },
  virement: { label: "Virement", color: "bg-purple-600" },
  mobile_money: { label: "Mobile Money", color: "bg-orange-500" },
};

const formatFCFA = (n) =>
  new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n || 0) + " FCFA";
const formatDate = (s) => (s ? new Date(s).toLocaleDateString("fr-FR") : "-");

export default function Paiements() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = user && ["super_admin", "directeur_general", "comptable"].includes(user.role);

  const [paiements, setPaiements] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ mode_paiement: "", client_id: "", q: "" });
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    listClients({ actif: true, limit: 200 }).then((d) => setClients(d.items || d)).catch(() => {});
    fetchPaiements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchPaiements = async () => {
    setLoading(true);
    try {
      const data = await getPaiements({ ...filters });
      setPaiements(data);
    } catch (e) {
      toast.error("Erreur chargement paiements");
    } finally {
      setLoading(false);
    }
  };

  const totals = paiements.reduce(
    (acc, p) => {
      acc.total += p.montant_total;
      acc.affecte += p.montant_affecte;
      acc.non_affecte += p.montant_non_affecte;
      return acc;
    },
    { total: 0, affecte: 0, non_affecte: 0 }
  );

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="paiements-page">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Paiements</h1>
            <p className="text-gray-600 dark:text-white/60 mt-1">
              Règlements clients (espèces, chèque, virement, mobile money)
            </p>
          </div>
          {canWrite && (
            <Button
              onClick={() => setShowForm(true)}
              className="bg-[#FF6200] hover:bg-[#E55900] text-white"
              data-testid="btn-nouveau-paiement"
            >
              <Plus className="h-4 w-4 mr-2" /> Nouveau paiement
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total encaissé</CardDescription>
              <CardTitle className="text-2xl text-green-600">{formatFCFA(totals.total)}</CardTitle>
            </CardHeader>
            <CardContent><Wallet className="h-4 w-4 text-green-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Affecté aux factures</CardDescription>
              <CardTitle className="text-2xl text-blue-600">{formatFCFA(totals.affecte)}</CardTitle>
            </CardHeader>
            <CardContent><ArrowLeftRight className="h-4 w-4 text-blue-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Non affecté</CardDescription>
              <CardTitle className="text-2xl text-orange-600">{formatFCFA(totals.non_affecte)}</CardTitle>
            </CardHeader>
            <CardContent><CreditCard className="h-4 w-4 text-orange-500" /></CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center"><Filter className="h-5 w-5 mr-2" /> Filtres</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label>Référence</Label>
                <Input
                  placeholder="FABS-REG-..."
                  value={filters.q}
                  onChange={(e) => setFilters({ ...filters, q: e.target.value })}
                  data-testid="input-search-paiement"
                />
              </div>
              <div>
                <Label>Mode</Label>
                <Select value={filters.mode_paiement || "all"} onValueChange={(v) => setFilters({ ...filters, mode_paiement: v === "all" ? "" : v })}>
                  <SelectTrigger data-testid="select-mode"><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {Object.entries(MODES).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Client</Label>
                <Select value={filters.client_id || "all"} onValueChange={(v) => setFilters({ ...filters, client_id: v === "all" ? "" : v })}>
                  <SelectTrigger data-testid="select-client"><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {(clients || []).map((c) => (
                      <SelectItem key={c.client_id} value={c.client_id}>{c.nom}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button onClick={fetchPaiements} data-testid="btn-appliquer">Appliquer</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Liste des paiements</CardTitle>
            <CardDescription>{paiements.length} paiement(s)</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
            ) : paiements.length === 0 ? (
              <div className="text-center py-12 text-gray-500">Aucun paiement</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left">
                      <th className="pb-3 font-semibold">Référence</th>
                      <th className="pb-3 font-semibold">Date</th>
                      <th className="pb-3 font-semibold">Client</th>
                      <th className="pb-3 font-semibold">Mode</th>
                      <th className="pb-3 font-semibold text-right">Montant</th>
                      <th className="pb-3 font-semibold text-right">Affecté</th>
                      <th className="pb-3 font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paiements.map((p) => (
                      <tr
                        key={p.paiement_id}
                        className="border-b hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer"
                        onClick={() => navigate(`/paiements/${p.paiement_id}`)}
                        data-testid={`row-paiement-${p.reference}`}
                      >
                        <td className="py-3 font-mono text-sm">{p.reference}</td>
                        <td className="py-3 text-sm">{formatDate(p.date_paiement)}</td>
                        <td className="py-3">{p.client_nom || "-"}</td>
                        <td className="py-3">
                          <Badge className={`${MODES[p.mode_paiement]?.color || "bg-gray-500"} text-white`}>
                            {MODES[p.mode_paiement]?.label || p.mode_paiement}
                          </Badge>
                        </td>
                        <td className="py-3 text-right font-semibold">{formatFCFA(p.montant_total)}</td>
                        <td className="py-3 text-right">{formatFCFA(p.montant_affecte)}</td>
                        <td className="py-3">
                          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/paiements/${p.paiement_id}`); }}>
                            Voir
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <PaiementFormDialog
          open={showForm}
          onOpenChange={setShowForm}
          clients={clients}
          onCreated={() => { setShowForm(false); fetchPaiements(); }}
        />
      </div>
    </DashboardLayout>
  );
}

function PaiementFormDialog({ open, onOpenChange, clients, onCreated }) {
  const [form, setForm] = useState({
    client_id: "",
    date_paiement: new Date().toISOString().slice(0, 10),
    mode_paiement: "especes",
    montant_total: "",
    banque: "",
    numero_cheque: "",
    reference_virement: "",
    operateur: "",
    numero_transaction: "",
    notes: "",
  });
  const [factures, setFactures] = useState([]);
  const [affectations, setAffectations] = useState({}); // { facture_id: montant }
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (form.client_id) {
      getFactures({ client_id: form.client_id, limit: 50 })
        .then((data) => setFactures((data || []).filter((f) => f.montant_restant > 0)))
        .catch(() => setFactures([]));
    } else {
      setFactures([]);
    }
    setAffectations({});
  }, [form.client_id]);

  const handleSubmit = async () => {
    if (!form.client_id || !form.montant_total) {
      toast.error("Client et montant sont obligatoires");
      return;
    }
    const factures_affectees = Object.entries(affectations)
      .filter(([_, m]) => parseFloat(m) > 0)
      .map(([facture_id, montant_affecte]) => ({ facture_id, montant_affecte: parseFloat(montant_affecte) }));

    try {
      setSaving(true);
      await createPaiement({
        ...form,
        montant_total: parseFloat(form.montant_total),
        factures: factures_affectees,
      });
      toast.success("Paiement enregistré");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur enregistrement paiement");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="dialog-paiement">
        <DialogHeader>
          <DialogTitle>Nouveau paiement</DialogTitle>
          <DialogDescription>Enregistrer un règlement client</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Client *</Label>
              <Select value={form.client_id} onValueChange={(v) => setForm({ ...form, client_id: v })}>
                <SelectTrigger data-testid="form-client"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {(clients || []).map((c) => (
                    <SelectItem key={c.client_id} value={c.client_id}>{c.nom}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Date *</Label>
              <Input
                type="date"
                value={form.date_paiement}
                onChange={(e) => setForm({ ...form, date_paiement: e.target.value })}
                data-testid="form-date"
              />
            </div>
            <div>
              <Label>Mode *</Label>
              <Select value={form.mode_paiement} onValueChange={(v) => setForm({ ...form, mode_paiement: v })}>
                <SelectTrigger data-testid="form-mode"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(MODES).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Montant total (FCFA) *</Label>
              <Input
                type="number"
                value={form.montant_total}
                onChange={(e) => setForm({ ...form, montant_total: e.target.value })}
                data-testid="form-montant"
              />
            </div>
          </div>

          {form.mode_paiement === "cheque" && (
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Banque</Label><Input value={form.banque} onChange={(e) => setForm({ ...form, banque: e.target.value })} /></div>
              <div><Label>N° chèque</Label><Input value={form.numero_cheque} onChange={(e) => setForm({ ...form, numero_cheque: e.target.value })} /></div>
            </div>
          )}
          {form.mode_paiement === "virement" && (
            <div><Label>Référence virement</Label><Input value={form.reference_virement} onChange={(e) => setForm({ ...form, reference_virement: e.target.value })} /></div>
          )}
          {form.mode_paiement === "mobile_money" && (
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Opérateur</Label><Input placeholder="Orange / MTN / Moov / Wave" value={form.operateur} onChange={(e) => setForm({ ...form, operateur: e.target.value })} /></div>
              <div><Label>N° transaction</Label><Input value={form.numero_transaction} onChange={(e) => setForm({ ...form, numero_transaction: e.target.value })} /></div>
            </div>
          )}

          {factures.length > 0 && (
            <div>
              <Label>Affecter aux factures</Label>
              <div className="border rounded-md p-3 space-y-2 mt-1">
                {factures.map((f) => (
                  <div key={f.facture_id} className="flex items-center gap-3">
                    <div className="flex-1 text-sm">
                      <span className="font-mono">{f.reference}</span>{" "}
                      <span className="text-gray-500">— Restant {formatFCFA(f.montant_restant)}</span>
                    </div>
                    <Input
                      type="number"
                      placeholder="0"
                      className="w-32"
                      value={affectations[f.facture_id] || ""}
                      onChange={(e) => setAffectations({ ...affectations, [f.facture_id]: e.target.value })}
                      data-testid={`affect-${f.reference}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <Label>Notes</Label>
            <Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-paiement">
            {saving ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
