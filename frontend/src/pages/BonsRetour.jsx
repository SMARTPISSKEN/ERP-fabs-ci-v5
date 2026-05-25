/**
 * Page Bons de Retour — Sprint 11
 */
import React, { useState, useEffect } from "react";
import { Plus, RotateCcw, CheckCircle, Filter, Trash2 } from "lucide-react";
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

import { getBonsRetour, createBonRetour, validerBonRetour } from "../services/bonsRetourApi";
import { getFactures } from "../services/facturesApi";
import { listClients } from "../services/clientsApi";
import { listProducts } from "../services/produitsApi";
import { useAuth } from "../hooks/useAuth";
import DocumentActions from "../components/documents/DocumentActions";

const STATUTS = {
  en_attente: { label: "En attente", color: "bg-yellow-500" },
  valide: { label: "Validé", color: "bg-blue-500" },
  avoir_genere: { label: "Avoir généré", color: "bg-green-600" },
  annule: { label: "Annulé", color: "bg-red-500" },
};

const fmt = (n) => new Intl.NumberFormat("fr-FR").format(n || 0) + " FCFA";
const formatDate = (s) => (s ? new Date(s).toLocaleDateString("fr-FR") : "-");

export default function BonsRetour() {
  const { user } = useAuth();
  const canWrite = user && ["super_admin", "directeur_general", "service_logistique", "comptable"].includes(user.role);

  const [brs, setBrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statut, setStatut] = useState("");
  const [showForm, setShowForm] = useState(false);

  useEffect(() => { fetchBrs(); /* eslint-disable-next-line */ }, []);

  const fetchBrs = async () => {
    setLoading(true);
    try {
      const data = await getBonsRetour({ statut, limit: 100 });
      setBrs(data);
    } catch (e) {
      toast.error("Erreur chargement BR");
    } finally {
      setLoading(false);
    }
  };

  const handleValider = async (brId) => {
    try {
      await validerBonRetour(brId);
      toast.success("BR validé et avoir généré");
      fetchBrs();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="bons-retour-page">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Bons de retour</h1>
            <p className="text-gray-600 dark:text-white/60 mt-1">Retours clients FABS-BR-26-27 — génération automatique d'avoirs</p>
          </div>
          {canWrite && (
            <Button onClick={() => setShowForm(true)} className="bg-[#FF6200] hover:bg-[#E55900] text-white" data-testid="btn-nouveau-br">
              <Plus className="h-4 w-4 mr-2" /> Nouveau retour
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card><CardHeader className="pb-2"><CardDescription>Total retours</CardDescription><CardTitle className="text-2xl">{brs.length}</CardTitle></CardHeader><CardContent><RotateCcw className="h-4 w-4 text-gray-500" /></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardDescription>En attente</CardDescription><CardTitle className="text-2xl text-yellow-600">{brs.filter(b => b.statut === "en_attente").length}</CardTitle></CardHeader><CardContent /></Card>
          <Card><CardHeader className="pb-2"><CardDescription>Avoirs générés</CardDescription><CardTitle className="text-2xl text-green-600">{brs.filter(b => b.statut === "avoir_genere").length}</CardTitle></CardHeader><CardContent><CheckCircle className="h-4 w-4 text-green-500" /></CardContent></Card>
        </div>

        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center"><Filter className="h-5 w-5 mr-2" />Filtres</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Statut</Label>
                <Select value={statut || "all"} onValueChange={(v) => setStatut(v === "all" ? "" : v)}>
                  <SelectTrigger data-testid="filter-statut"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {Object.entries(STATUTS).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end"><Button onClick={fetchBrs} data-testid="btn-appliquer">Appliquer</Button></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Liste des bons de retour</CardTitle><CardDescription>{brs.length} retour(s)</CardDescription></CardHeader>
          <CardContent>
            {loading ? <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
              : brs.length === 0 ? <div className="text-center py-12 text-gray-500">Aucun bon de retour</div>
              : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b">
                      <tr className="text-left">
                        <th className="pb-3 font-semibold">Référence</th>
                        <th className="pb-3 font-semibold">Facture</th>
                        <th className="pb-3 font-semibold">Client</th>
                        <th className="pb-3 font-semibold">Date</th>
                        <th className="pb-3 font-semibold text-right">Montant TTC</th>
                        <th className="pb-3 font-semibold">Avoir</th>
                        <th className="pb-3 font-semibold">Statut</th>
                        <th className="pb-3 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {brs.map((br) => (
                        <tr key={br.br_id} className="border-b hover:bg-gray-50 dark:hover:bg-white/5" data-testid={`row-br-${br.reference}`}>
                          <td className="py-3 font-mono text-sm">{br.reference}</td>
                          <td className="py-3 font-mono text-xs">{br.facture_reference}</td>
                          <td className="py-3">{br.client_nom || "-"}</td>
                          <td className="py-3 text-sm">{formatDate(br.date_retour)}</td>
                          <td className="py-3 text-right font-semibold">{fmt(br.montant_total_ttc)}</td>
                          <td className="py-3 font-mono text-xs">{br.avoir_reference || "-"}</td>
                          <td className="py-3"><Badge className={`${STATUTS[br.statut]?.color} text-white`}>{STATUTS[br.statut]?.label}</Badge></td>
                          <td className="py-3">
                            <div className="flex flex-wrap gap-2">
                              <DocumentActions
                                pdfUrl={`/api/bons-retour/${br.br_id}/pdf`}
                                filename={`${br.reference}.pdf`}
                                message={`Bonjour, voici votre bon de retour ${br.reference}.`}
                                testIdPrefix={`br-${br.reference}`}
                              />
                              {br.statut === "en_attente" && canWrite && (
                                <Button size="sm" variant="outline" onClick={() => handleValider(br.br_id)} data-testid={`btn-valider-${br.reference}`}>
                                  Valider
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </CardContent>
        </Card>

        <BrFormDialog open={showForm} onOpenChange={setShowForm} onCreated={() => { setShowForm(false); fetchBrs(); }} />
      </div>
    </DashboardLayout>
  );
}

function BrFormDialog({ open, onOpenChange, onCreated }) {
  const [clients, setClients] = useState([]);
  const [factures, setFactures] = useState([]);
  const [produits, setProduits] = useState([]);
  const [clientId, setClientId] = useState("");
  const [factureId, setFactureId] = useState("");
  const [dateRetour, setDateRetour] = useState(new Date().toISOString().slice(0, 10));
  const [motifGlobal, setMotifGlobal] = useState("");
  const [lignes, setLignes] = useState([{ produit_id: "", quantite: 1, prix_unitaire: 0, motif: "" }]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      listClients({ actif: true, limit: 200 }).then((d) => setClients(d.items || d)).catch(() => {});
      listProducts({ actif: true, limit: 200 }).then((d) => setProduits(d.items || d || [])).catch(() => {});
      setClientId(""); setFactureId(""); setMotifGlobal(""); setLignes([{ produit_id: "", quantite: 1, prix_unitaire: 0, motif: "" }]);
    }
  }, [open]);

  useEffect(() => {
    if (clientId) getFactures({ client_id: clientId, type_facture: "facture", limit: 50 }).then(setFactures).catch(() => {});
    else setFactures([]);
  }, [clientId]);

  const updateLigne = (idx, key, value) => {
    setLignes((prev) => prev.map((l, i) => (i === idx ? { ...l, [key]: value } : l)));
  };
  const addLigne = () => setLignes([...lignes, { produit_id: "", quantite: 1, prix_unitaire: 0, motif: "" }]);
  const removeLigne = (idx) => setLignes(lignes.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (!clientId || !factureId || motifGlobal.length < 10) {
      toast.error("Client, facture et motif (10 car. min) obligatoires"); return;
    }
    if (lignes.some((l) => !l.produit_id || !l.quantite || !l.prix_unitaire || l.motif.length < 5)) {
      toast.error("Toutes les lignes : produit, quantité, prix, motif (5+ car.) requis"); return;
    }
    try {
      setSaving(true);
      await createBonRetour({
        facture_id: factureId,
        client_id: clientId,
        date_retour: dateRetour,
        motif_global: motifGlobal,
        lignes: lignes.map((l) => ({
          produit_id: l.produit_id,
          quantite: parseInt(l.quantite, 10),
          prix_unitaire: parseFloat(l.prix_unitaire),
          motif: l.motif,
        })),
      });
      toast.success("Bon de retour créé");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur création BR");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="dialog-br">
        <DialogHeader>
          <DialogTitle>Nouveau bon de retour</DialogTitle>
          <DialogDescription>Retour client — avoir généré à la validation</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Client *</Label>
              <Select value={clientId} onValueChange={setClientId}>
                <SelectTrigger data-testid="form-client"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {clients.map((c) => <SelectItem key={c.client_id} value={c.client_id}>{c.nom}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Facture *</Label>
              <Select value={factureId} onValueChange={setFactureId}>
                <SelectTrigger data-testid="form-facture"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
                <SelectContent>
                  {factures.map((f) => <SelectItem key={f.facture_id} value={f.facture_id}>{f.reference}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Date retour *</Label>
              <Input type="date" value={dateRetour} onChange={(e) => setDateRetour(e.target.value)} data-testid="form-date" />
            </div>
          </div>
          <div>
            <Label>Motif global * (min 10 car.)</Label>
            <Textarea rows={2} value={motifGlobal} onChange={(e) => setMotifGlobal(e.target.value)} data-testid="form-motif-global" />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <Label>Lignes de retour *</Label>
              <Button size="sm" variant="outline" onClick={addLigne} data-testid="btn-add-ligne"><Plus className="h-3 w-3 mr-1" /> Ligne</Button>
            </div>
            <div className="space-y-3">
              {lignes.map((l, idx) => (
                <div key={idx} className="border rounded-md p-3 space-y-2">
                  <div className="grid grid-cols-12 gap-2">
                    <div className="col-span-5">
                      <Select value={l.produit_id} onValueChange={(v) => updateLigne(idx, "produit_id", v)}>
                        <SelectTrigger data-testid={`ligne-produit-${idx}`}><SelectValue placeholder="Produit" /></SelectTrigger>
                        <SelectContent>
                          {produits.map((p) => <SelectItem key={p.product_id} value={p.product_id}>{p.titre}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <Input className="col-span-2" type="number" placeholder="Qté" value={l.quantite} onChange={(e) => updateLigne(idx, "quantite", e.target.value)} data-testid={`ligne-qte-${idx}`} />
                    <Input className="col-span-3" type="number" placeholder="PU FCFA" value={l.prix_unitaire} onChange={(e) => updateLigne(idx, "prix_unitaire", e.target.value)} data-testid={`ligne-pu-${idx}`} />
                    <div className="col-span-2 flex justify-end">
                      {lignes.length > 1 && (
                        <Button size="sm" variant="ghost" onClick={() => removeLigne(idx)}><Trash2 className="h-3 w-3" /></Button>
                      )}
                    </div>
                  </div>
                  <Input placeholder="Motif ligne (min 5 car.)" value={l.motif} onChange={(e) => updateLigne(idx, "motif", e.target.value)} data-testid={`ligne-motif-${idx}`} />
                </div>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-br">
            {saving ? "Création..." : "Créer le retour"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
