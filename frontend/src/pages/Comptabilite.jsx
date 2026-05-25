/**
 * Page Comptabilité — Sprint 12
 * Onglets : Écritures, Créances clients, Balance
 */
import React, { useState, useEffect } from "react";
import { Calculator, FileSpreadsheet, Users, BookOpen, Plus } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";

import { getEcritures, createEcriture, getCreances, getBalance } from "../services/comptabiliteApi";
import { useAuth } from "../hooks/useAuth";

const JOURNAUX = {
  ventes: "Ventes",
  achats: "Achats",
  banque: "Banque",
  caisse: "Caisse",
  operations_diverses: "OD",
};

const fmt = (n) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n || 0) + " FCFA";
const formatDate = (s) => (s ? new Date(s).toLocaleDateString("fr-FR") : "-");

export default function Comptabilite() {
  const { user } = useAuth();
  const canWrite = user && ["super_admin", "comptable"].includes(user.role);

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="comptabilite-page">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Comptabilité</h1>
          <p className="text-gray-600 dark:text-white/60 mt-1">Journaux, créances clients et balance comptable</p>
        </div>

        <Tabs defaultValue="ecritures">
          <TabsList>
            <TabsTrigger value="ecritures" data-testid="tab-ecritures"><BookOpen className="h-4 w-4 mr-2" /> Écritures</TabsTrigger>
            <TabsTrigger value="creances" data-testid="tab-creances"><Users className="h-4 w-4 mr-2" /> Créances clients</TabsTrigger>
            <TabsTrigger value="balance" data-testid="tab-balance"><FileSpreadsheet className="h-4 w-4 mr-2" /> Balance</TabsTrigger>
          </TabsList>

          <TabsContent value="ecritures"><EcrituresTab canWrite={canWrite} /></TabsContent>
          <TabsContent value="creances"><CreancesTab /></TabsContent>
          <TabsContent value="balance"><BalanceTab /></TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}

function EcrituresTab({ canWrite }) {
  const [ecritures, setEcritures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [journal, setJournal] = useState("");
  const [showForm, setShowForm] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      setEcritures(await getEcritures({ journal, limit: 200 }));
    } catch (e) { toast.error("Erreur chargement écritures"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); /* eslint-disable-next-line */ }, []);

  return (
    <Card className="mt-4">
      <CardHeader className="flex flex-row justify-between items-center">
        <div>
          <CardTitle>Journal comptable</CardTitle>
          <CardDescription>{ecritures.length} écriture(s)</CardDescription>
        </div>
        {canWrite && (
          <Button onClick={() => setShowForm(true)} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-nouvelle-ecriture">
            <Plus className="h-4 w-4 mr-2" /> Nouvelle écriture
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-4">
          <Select value={journal || "all"} onValueChange={(v) => setJournal(v === "all" ? "" : v)}>
            <SelectTrigger className="w-48" data-testid="filter-journal"><SelectValue placeholder="Tous les journaux" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous</SelectItem>
              {Object.entries(JOURNAUX).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={fetch} data-testid="btn-appliquer">Appliquer</Button>
        </div>

        {loading ? <Skeleton className="h-32 w-full" /> : ecritures.length === 0 ? (
          <div className="text-center py-12 text-gray-500">Aucune écriture</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left">
                  <th className="pb-3 font-semibold">Date</th>
                  <th className="pb-3 font-semibold">Journal</th>
                  <th className="pb-3 font-semibold">Compte</th>
                  <th className="pb-3 font-semibold">Libellé</th>
                  <th className="pb-3 font-semibold text-right">Débit</th>
                  <th className="pb-3 font-semibold text-right">Crédit</th>
                  <th className="pb-3 font-semibold">Pièce</th>
                </tr>
              </thead>
              <tbody>
                {ecritures.map((e) => (
                  <tr key={e.ecriture_id} className="border-b" data-testid={`row-ecr-${e.ecriture_id}`}>
                    <td className="py-3 text-sm">{formatDate(e.date_ecriture)}</td>
                    <td className="py-3 text-sm">{JOURNAUX[e.journal] || e.journal}</td>
                    <td className="py-3 font-mono text-sm">{e.compte}</td>
                    <td className="py-3 text-sm">{e.libelle}</td>
                    <td className="py-3 text-right text-green-600 font-mono">{e.debit > 0 ? fmt(e.debit) : ""}</td>
                    <td className="py-3 text-right text-red-600 font-mono">{e.credit > 0 ? fmt(e.credit) : ""}</td>
                    <td className="py-3 font-mono text-xs">{e.piece_reference || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>

      <EcritureFormDialog open={showForm} onOpenChange={setShowForm} onCreated={() => { setShowForm(false); fetch(); }} />
    </Card>
  );
}

function EcritureFormDialog({ open, onOpenChange, onCreated }) {
  const [form, setForm] = useState({
    journal: "ventes",
    date_ecriture: new Date().toISOString().slice(0, 10),
    compte: "",
    libelle: "",
    debit: "",
    credit: "",
    piece_reference: "",
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.compte || !form.libelle || (!form.debit && !form.credit)) {
      toast.error("Compte, libellé et débit OU crédit obligatoires"); return;
    }
    try {
      setSaving(true);
      await createEcriture({
        ...form,
        debit: parseFloat(form.debit || 0),
        credit: parseFloat(form.credit || 0),
        piece_reference: form.piece_reference || null,
      });
      toast.success("Écriture enregistrée");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="dialog-ecriture">
        <DialogHeader>
          <DialogTitle>Nouvelle écriture comptable</DialogTitle>
          <DialogDescription>Saisie manuelle d'une écriture de journal</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Journal *</Label>
              <Select value={form.journal} onValueChange={(v) => setForm({ ...form, journal: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(JOURNAUX).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Date *</Label>
              <Input type="date" value={form.date_ecriture} onChange={(e) => setForm({ ...form, date_ecriture: e.target.value })} />
            </div>
            <div>
              <Label>N° Compte *</Label>
              <Input placeholder="411000" value={form.compte} onChange={(e) => setForm({ ...form, compte: e.target.value })} data-testid="form-compte" />
            </div>
            <div>
              <Label>Pièce</Label>
              <Input placeholder="FABS-FA-..." value={form.piece_reference} onChange={(e) => setForm({ ...form, piece_reference: e.target.value })} />
            </div>
          </div>
          <div>
            <Label>Libellé *</Label>
            <Input value={form.libelle} onChange={(e) => setForm({ ...form, libelle: e.target.value })} data-testid="form-libelle" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Débit</Label>
              <Input type="number" value={form.debit} onChange={(e) => setForm({ ...form, debit: e.target.value, credit: "" })} data-testid="form-debit" />
            </div>
            <div>
              <Label>Crédit</Label>
              <Input type="number" value={form.credit} onChange={(e) => setForm({ ...form, credit: e.target.value, debit: "" })} data-testid="form-credit" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-ecriture">
            {saving ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreancesTab() {
  const [creances, setCreances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCreances().then(setCreances).catch(() => toast.error("Erreur chargement créances")).finally(() => setLoading(false));
  }, []);

  const totalRestant = creances.reduce((s, c) => s + c.montant_restant, 0);

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Créances clients</CardTitle>
        <CardDescription>
          {creances.length} client(s) débiteur(s) — total restant dû : <span className="font-bold text-orange-600">{fmt(totalRestant)}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-32 w-full" /> : creances.length === 0 ? (
          <div className="text-center py-12 text-gray-500">Aucune créance — toutes les factures sont réglées 🎉</div>
        ) : (
          <table className="w-full">
            <thead className="border-b">
              <tr className="text-left">
                <th className="pb-3 font-semibold">Client</th>
                <th className="pb-3 font-semibold text-center">Nb factures</th>
                <th className="pb-3 font-semibold text-right">Total facturé</th>
                <th className="pb-3 font-semibold text-right">Payé</th>
                <th className="pb-3 font-semibold text-right">Restant dû</th>
              </tr>
            </thead>
            <tbody>
              {creances.map((c) => (
                <tr key={c.client_id} className="border-b" data-testid={`row-creance-${c.client_id}`}>
                  <td className="py-3 font-semibold">{c.client_nom}</td>
                  <td className="py-3 text-center">{c.nombre_factures}</td>
                  <td className="py-3 text-right">{fmt(c.montant_total_factures)}</td>
                  <td className="py-3 text-right text-green-600">{fmt(c.montant_total_paye)}</td>
                  <td className="py-3 text-right font-bold text-orange-600">{fmt(c.montant_restant)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function BalanceTab() {
  const [balance, setBalance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBalance().then(setBalance).catch(() => toast.error("Erreur chargement balance")).finally(() => setLoading(false));
  }, []);

  const totals = balance.reduce(
    (acc, b) => { acc.debit += b.total_debit; acc.credit += b.total_credit; return acc; },
    { debit: 0, credit: 0 }
  );

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Balance comptable</CardTitle>
        <CardDescription>
          Total débit : <span className="font-bold text-green-600">{fmt(totals.debit)}</span> · Total crédit :{" "}
          <span className="font-bold text-red-600">{fmt(totals.credit)}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-32 w-full" /> : balance.length === 0 ? (
          <div className="text-center py-12 text-gray-500"><Calculator className="h-12 w-12 mx-auto text-gray-400 mb-4" />Aucune écriture</div>
        ) : (
          <table className="w-full">
            <thead className="border-b">
              <tr className="text-left">
                <th className="pb-3 font-semibold">N° Compte</th>
                <th className="pb-3 font-semibold text-right">Total débit</th>
                <th className="pb-3 font-semibold text-right">Total crédit</th>
                <th className="pb-3 font-semibold text-right">Solde</th>
              </tr>
            </thead>
            <tbody>
              {balance.map((b) => (
                <tr key={b.compte} className="border-b" data-testid={`row-balance-${b.compte}`}>
                  <td className="py-3 font-mono">{b.compte}</td>
                  <td className="py-3 text-right">{fmt(b.total_debit)}</td>
                  <td className="py-3 text-right">{fmt(b.total_credit)}</td>
                  <td className={`py-3 text-right font-bold ${b.solde >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {fmt(b.solde)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
