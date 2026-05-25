/**
 * Page Bons de Livraison — Sprint 10
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Truck, CheckCircle, Clock, Filter } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

import { getBonsLivraison, createBonLivraison, livrerBon } from "../services/bonsLivraisonApi";
import { getCommandes, getCommande } from "../services/commandesApi";
import { useAuth } from "../hooks/useAuth";
import DocumentActions from "../components/documents/DocumentActions";

const STATUTS = {
  en_preparation: { label: "En préparation", color: "bg-yellow-500" },
  pret: { label: "Prêt", color: "bg-blue-500" },
  livre: { label: "Livré", color: "bg-green-600" },
  annule: { label: "Annulé", color: "bg-red-500" },
};

const formatDate = (s) => (s ? new Date(s).toLocaleDateString("fr-FR") : "-");

export default function BonsLivraison() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = user && ["super_admin", "directeur_general", "service_logistique"].includes(user.role);

  const [bls, setBls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statut, setStatut] = useState("");
  const [showForm, setShowForm] = useState(false);

  useEffect(() => { fetchBls(); /* eslint-disable-next-line */ }, []);

  const fetchBls = async () => {
    setLoading(true);
    try {
      const data = await getBonsLivraison({ statut, limit: 100 });
      setBls(data);
    } catch (e) {
      toast.error("Erreur chargement BL");
    } finally {
      setLoading(false);
    }
  };

  const handleLivrer = async (blId) => {
    try {
      await livrerBon(blId);
      toast.success("BL marqué comme livré");
      fetchBls();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    }
  };

  const stats = bls.reduce(
    (acc, b) => {
      if (b.statut === "en_preparation" || b.statut === "pret") acc.en_cours += 1;
      else if (b.statut === "livre") acc.livres += 1;
      return acc;
    },
    { en_cours: 0, livres: 0 }
  );

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="bons-livraison-page">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Bons de livraison</h1>
            <p className="text-gray-600 dark:text-white/60 mt-1">Gestion des livraisons FABS-BL-26-27</p>
          </div>
          {canWrite && (
            <Button onClick={() => setShowForm(true)} className="bg-[#FF6200] hover:bg-[#E55900] text-white" data-testid="btn-nouveau-bl">
              <Plus className="h-4 w-4 mr-2" /> Nouveau BL
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2"><CardDescription>Total BL</CardDescription><CardTitle className="text-2xl">{bls.length}</CardTitle></CardHeader>
            <CardContent><Truck className="h-4 w-4 text-gray-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardDescription>En cours</CardDescription><CardTitle className="text-2xl text-yellow-600">{stats.en_cours}</CardTitle></CardHeader>
            <CardContent><Clock className="h-4 w-4 text-yellow-500" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardDescription>Livrés</CardDescription><CardTitle className="text-2xl text-green-600">{stats.livres}</CardTitle></CardHeader>
            <CardContent><CheckCircle className="h-4 w-4 text-green-500" /></CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center"><Filter className="h-5 w-5 mr-2" />Filtres</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Statut</Label>
                <Select value={statut || "all"} onValueChange={(v) => setStatut(v === "all" ? "" : v)}>
                  <SelectTrigger data-testid="filter-statut"><SelectValue placeholder="Tous" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {Object.entries(STATUTS).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end"><Button onClick={fetchBls} data-testid="btn-appliquer">Appliquer</Button></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Liste des BL</CardTitle><CardDescription>{bls.length} bon(s) de livraison</CardDescription></CardHeader>
          <CardContent>
            {loading ? <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
              : bls.length === 0 ? <div className="text-center py-12 text-gray-500">Aucun BL</div>
              : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b">
                      <tr className="text-left">
                        <th className="pb-3 font-semibold">Référence</th>
                        <th className="pb-3 font-semibold">Commande</th>
                        <th className="pb-3 font-semibold">Client</th>
                        <th className="pb-3 font-semibold">Date création</th>
                        <th className="pb-3 font-semibold">Livraison prévue</th>
                        <th className="pb-3 font-semibold">Statut</th>
                        <th className="pb-3 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bls.map((bl) => (
                        <tr key={bl.bl_id} className="border-b hover:bg-gray-50 dark:hover:bg-white/5" data-testid={`row-bl-${bl.reference}`}>
                          <td className="py-3 font-mono text-sm">{bl.reference}</td>
                          <td className="py-3 font-mono text-xs">{bl.commande_reference}</td>
                          <td className="py-3">{bl.client_nom || "-"}</td>
                          <td className="py-3 text-sm">{formatDate(bl.date_creation)}</td>
                          <td className="py-3 text-sm">{formatDate(bl.date_livraison_prevue)}</td>
                          <td className="py-3"><Badge className={`${STATUTS[bl.statut]?.color} text-white`}>{STATUTS[bl.statut]?.label}</Badge></td>
                          <td className="py-3">
                            <div className="flex flex-wrap gap-2">
                              <DocumentActions
                                pdfUrl={`/api/bons-livraison/${bl.bl_id}/pdf`}
                                filename={`${bl.reference}.pdf`}
                                message={`Bonjour, voici votre bon de livraison ${bl.reference}.`}
                                testIdPrefix={`bl-${bl.reference}`}
                              />
                              {bl.statut !== "livre" && canWrite && (
                                <Button size="sm" variant="outline" onClick={() => handleLivrer(bl.bl_id)} data-testid={`btn-livrer-${bl.reference}`}>
                                  Marquer livré
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

        <BlFormDialog open={showForm} onOpenChange={setShowForm} onCreated={() => { setShowForm(false); fetchBls(); }} />
      </div>
    </DashboardLayout>
  );
}

function BlFormDialog({ open, onOpenChange, onCreated }) {
  const [commandes, setCommandes] = useState([]);
  const [commandeId, setCommandeId] = useState("");
  const [commandeDetail, setCommandeDetail] = useState(null);
  const [dateLivraisonPrevue, setDateLivraisonPrevue] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      getCommandes({ statut: "preparee", limit: 50 }).then(setCommandes).catch(() => {});
      setCommandeId(""); setCommandeDetail(null); setNotes(""); setDateLivraisonPrevue("");
    }
  }, [open]);

  useEffect(() => {
    if (commandeId) getCommande(commandeId).then(setCommandeDetail).catch(() => setCommandeDetail(null));
    else setCommandeDetail(null);
  }, [commandeId]);

  const handleSubmit = async () => {
    if (!commandeId) { toast.error("Sélectionner une commande"); return; }
    if (!commandeDetail?.lignes?.length) { toast.error("Commande sans lignes"); return; }
    const lignes = commandeDetail.lignes.map((l) => ({ produit_id: l.produit_id, quantite: l.quantite }));
    try {
      setSaving(true);
      await createBonLivraison({
        commande_id: commandeId,
        date_livraison_prevue: dateLivraisonPrevue || null,
        notes: notes || null,
        lignes,
      });
      toast.success("BL créé");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur création BL");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="dialog-bl">
        <DialogHeader>
          <DialogTitle>Nouveau bon de livraison</DialogTitle>
          <DialogDescription>Créer un BL à partir d'une commande préparée</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Commande préparée *</Label>
            <Select value={commandeId} onValueChange={setCommandeId}>
              <SelectTrigger data-testid="form-commande"><SelectValue placeholder="Sélectionner..." /></SelectTrigger>
              <SelectContent>
                {commandes.map((c) => <SelectItem key={c.commande_id} value={c.commande_id}>{c.reference} — {c.client_nom || "-"}</SelectItem>)}
              </SelectContent>
            </Select>
            {commandes.length === 0 && <p className="text-[11px] text-orange-600 mt-1">Aucune commande au statut « préparée ».</p>}
          </div>
          <div>
            <Label>Date livraison prévue</Label>
            <Input type="date" value={dateLivraisonPrevue} onChange={(e) => setDateLivraisonPrevue(e.target.value)} data-testid="form-date" />
          </div>
          <div>
            <Label>Notes</Label>
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          {commandeDetail && (
            <div className="text-xs text-gray-500 border rounded-md p-2">
              {commandeDetail.lignes?.length} ligne(s) seront copiées dans le BL.
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-bl">
            {saving ? "Création..." : "Créer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
