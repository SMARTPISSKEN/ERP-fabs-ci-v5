/**
 * Page Détail Paiement — Sprint 8
 */
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Receipt } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";

import { getPaiement } from "../services/paiementsApi";

const MODES = {
  especes: { label: "Espèces", color: "bg-green-600" },
  cheque: { label: "Chèque", color: "bg-blue-600" },
  virement: { label: "Virement", color: "bg-purple-600" },
  mobile_money: { label: "Mobile Money", color: "bg-orange-500" },
};

const fmt = (n) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n || 0) + " FCFA";

export default function PaiementDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [paiement, setPaiement] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPaiement(id)
      .then(setPaiement)
      .catch(() => { toast.error("Paiement introuvable"); navigate("/paiements"); })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  if (loading) {
    return (
      <DashboardLayout>
        <Skeleton className="h-12 w-64 mb-4" /><Skeleton className="h-64 w-full" />
      </DashboardLayout>
    );
  }
  if (!paiement) return null;

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="paiement-detail">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/paiements")} data-testid="btn-retour">
            <ArrowLeft className="h-4 w-4 mr-2" /> Retour
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">{paiement.reference}</h1>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={`${MODES[paiement.mode_paiement]?.color} text-white`}>
                {MODES[paiement.mode_paiement]?.label}
              </Badge>
              <span className="text-sm text-gray-500">{paiement.date_paiement}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader><CardTitle>Informations client</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div><span className="text-gray-500">Client :</span> <span className="font-medium">{paiement.client_nom}</span></div>
                  {paiement.banque && <div><span className="text-gray-500">Banque :</span> {paiement.banque}</div>}
                  {paiement.numero_cheque && <div><span className="text-gray-500">N° chèque :</span> {paiement.numero_cheque}</div>}
                  {paiement.reference_virement && <div><span className="text-gray-500">Réf virement :</span> {paiement.reference_virement}</div>}
                  {paiement.operateur && <div><span className="text-gray-500">Opérateur :</span> {paiement.operateur}</div>}
                  {paiement.numero_transaction && <div><span className="text-gray-500">N° transaction :</span> {paiement.numero_transaction}</div>}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Receipt className="h-5 w-5" /> Factures affectées</CardTitle></CardHeader>
              <CardContent>
                {paiement.factures?.length === 0 ? (
                  <p className="text-gray-500 text-sm">Aucune affectation — montant entièrement non affecté.</p>
                ) : (
                  <div className="space-y-2">
                    {paiement.factures.map((f) => (
                      <div key={f.facture_id} className="flex justify-between items-center border-b pb-2">
                        <span className="font-mono text-sm">{f.facture_reference}</span>
                        <span className="font-semibold text-green-600">{fmt(f.montant_affecte)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {paiement.notes && (
              <Card>
                <CardHeader><CardTitle>Notes</CardTitle></CardHeader>
                <CardContent><p className="whitespace-pre-wrap">{paiement.notes}</p></CardContent>
              </Card>
            )}
          </div>

          <div>
            <Card>
              <CardHeader><CardTitle>Résumé</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between"><span>Montant total</span><span className="font-bold text-[#FF6200]">{fmt(paiement.montant_total)}</span></div>
                <Separator />
                <div className="flex justify-between"><span>Affecté</span><span className="text-green-600 font-semibold">{fmt(paiement.montant_affecte)}</span></div>
                <div className="flex justify-between"><span>Non affecté</span><span className="text-orange-600 font-semibold">{fmt(paiement.montant_non_affecte)}</span></div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
