/**
 * Page détail facture avec actions
 * Sprint 7
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Send, DollarSign } from 'lucide-react';
import { getFacture, emettreFacture, genererAvoir } from '../services/facturesApi';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Skeleton } from '../components/ui/skeleton';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { useAuth } from '../hooks/useAuth';
import DashboardLayout from '../components/layout/DashboardLayout';
import DocumentActions from '../components/documents/DocumentActions';

const STATUT_CONFIG = {
  brouillon: { label: 'Brouillon', color: 'bg-gray-500' },
  emise: { label: 'Émise', color: 'bg-blue-500' },
  partiellement_payee: { label: 'Partiellement payée', color: 'bg-orange-500' },
  payee: { label: 'Payée', color: 'bg-green-500' },
  annulee: { label: 'Annulée', color: 'bg-red-500' },
};

export default function FactureDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [facture, setFacture] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showAvoirDialog, setShowAvoirDialog] = useState(false);
  const [avoirData, setAvoirData] = useState({ montant: '', motif: '' });

  useEffect(() => {
    fetchFacture();
  }, [id]);

  const fetchFacture = async () => {
    setLoading(true);
    try {
      const data = await getFacture(id);
      // S'assurer que lignes est un tableau
      const factureData = {
        ...data,
        lignes: Array.isArray(data?.lignes) ? data.lignes : [],
      };
      setFacture(factureData);
      setAvoirData(prev => ({ ...prev, montant: data.montant_ttc }));
    } catch (error) {
      toast.error('Erreur lors du chargement de la facture');
      navigate('/factures');
    } finally {
      setLoading(false);
    }
  };

  const handleEmettre = async () => {
    setActionLoading(true);
    try {
      const updated = await emettreFacture(id);
      // S'assurer que lignes est un tableau
      const factureData = {
        ...updated,
        lignes: Array.isArray(updated?.lignes) ? updated.lignes : [],
      };
      setFacture(factureData);
      toast.success('Facture émise avec succès');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'émission');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenererAvoir = async () => {
    if (!avoirData.montant || !avoirData.motif || avoirData?.motif?.length < 10) {
      toast.error('Veuillez remplir tous les champs (motif min 10 caractères)');
      return;
    }
    
    setActionLoading(true);
    try {
      await genererAvoir(id, parseFloat(avoirData.montant), avoirData.motif);
      toast.success('Avoir généré avec succès');
      setShowAvoirDialog(false);
      fetchFacture();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de la génération de l\'avoir');
    } finally {
      setActionLoading(false);
    }
  };

  const canEmit = () => {
    return user && ['super_admin', 'directeur_general', 'directeur_commercial', 'comptable'].includes(user.role);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + ' FCFA';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <Skeleton className="h-12 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      </DashboardLayout>
    );
  }

  if (!facture) return null;

  return (
    <DashboardLayout>
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/factures')}
            data-testid="btn-retour"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">
              {facture.reference}
            </h1>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={`${STATUT_CONFIG[facture.statut].color} text-white`}>
                {STATUT_CONFIG[facture.statut].label}
              </Badge>
              {facture.type_facture === 'avoir' && (
                <Badge variant="outline" className="text-red-600 border-red-600">
                  Avoir
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 items-center">
          <DocumentActions
            pdfUrl={`/api/factures/${facture.facture_id}/pdf`}
            filename={`${facture.reference}.pdf`}
            phone={facture.client_telephone}
            message={`Bonjour, voici votre facture ${facture.reference}. Merci.`}
            testIdPrefix="facture"
          />
          {facture.statut === 'brouillon' && canEmit() && (
            <Button
              onClick={handleEmettre}
              disabled={actionLoading}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="btn-emettre"
            >
              <Send className="h-4 w-4 mr-2" />
              Émettre
            </Button>
          )}

          {facture.type_facture === 'facture' && canEmit() && (
            <Button
              variant="outline"
              onClick={() => setShowAvoirDialog(true)}
              disabled={actionLoading}
              data-testid="btn-generer-avoir"
            >
              <FileText className="h-4 w-4 mr-2" />
              Générer avoir
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Client Info */}
          <Card>
            <CardHeader>
              <CardTitle>Informations client</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">Nom:</span>{' '}
                  <span className="font-medium">{facture.client_nom || '-'}</span>
                </div>
                <div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">Date facture:</span>{' '}
                  <span className="font-medium">{formatDate(facture.date_facture)}</span>
                </div>
                {facture.date_echeance && (
                  <div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Date échéance:</span>{' '}
                    <span className="font-medium">{formatDate(facture.date_echeance)}</span>
                  </div>
                )}
                {facture.commande_reference && (
                  <div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Commande:</span>{' '}
                    <span className="font-medium font-mono">{facture.commande_reference}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Lignes */}
          <Card>
            <CardHeader>
              <CardTitle>Lignes de facture</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Array.isArray(facture?.lignes) && facture.lignes.map((ligne) => (
                  <div key={ligne.ligne_id} className="flex justify-between items-start border-b pb-3 last:border-0">
                    <div className="flex-1">
                      <div className="font-medium">{ligne.designation}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Qté: {ligne.quantite} × {formatCurrency(ligne.prix_unitaire)}
                      </div>
                      {ligne.remise_ligne > 0 && (
                        <Badge variant="outline" className="mt-1 text-orange-600">
                          Remise: -{ligne.remise_ligne}%
                        </Badge>
                      )}
                    </div>
                    <div className="font-semibold">
                      {formatCurrency(ligne.montant_ht)}
                    </div>
                  </div>
                ))}
              </div>

              <Separator className="my-4" />

              {/* Totals */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Sous-total HT:</span>
                  <span>{formatCurrency(facture.montant_ht + (facture.montant_ht * facture.remise_globale / 100))}</span>
                </div>
                {facture.remise_globale > 0 && (
                  <div className="flex justify-between text-sm text-orange-600">
                    <span>Remise globale ({facture.remise_globale}%):</span>
                    <span>-{formatCurrency(facture.montant_ht * facture.remise_globale / 100)}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span>Montant HT:</span>
                  <span>{formatCurrency(facture.montant_ht)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>TVA (18%):</span>
                  <span>{formatCurrency(facture.montant_tva)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-lg font-bold">
                  <span>Total TTC:</span>
                  <span className="text-[#FF6200]">{formatCurrency(facture.montant_ttc)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Montant réglé:</span>
                  <span className="text-green-600 font-semibold">{formatCurrency(facture.montant_regle)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Restant dû:</span>
                  <span className="text-orange-600 font-semibold">{formatCurrency(facture.montant_restant)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {facture.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{facture.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Résumé</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Type</div>
                <div className="font-semibold">{facture.type_facture === 'facture' ? 'Facture' : 'Avoir'}</div>
              </div>
              <Separator />
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Statut</div>
                <div className="font-semibold">{STATUT_CONFIG[facture.statut].label}</div>
              </div>
              <Separator />
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Date émission</div>
                <div className="font-semibold">{formatDate(facture.date_emission)}</div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog Générer Avoir */}
      <Dialog open={showAvoirDialog} onOpenChange={setShowAvoirDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Générer un avoir</DialogTitle>
            <DialogDescription>
              Créer un avoir (note de crédit) pour cette facture
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="montant-avoir">Montant de l'avoir (FCFA)</Label>
              <Input
                id="montant-avoir"
                type="number"
                min="0"
                max={facture.montant_ttc}
                value={avoirData.montant}
                onChange={(e) => setAvoirData(prev => ({ ...prev, montant: e.target.value }))}
                data-testid="input-montant-avoir"
              />
              <p className="text-sm text-gray-500 mt-1">Maximum: {formatCurrency(facture.montant_ttc)}</p>
            </div>
            <div>
              <Label htmlFor="motif-avoir">Motif (minimum 10 caractères)</Label>
              <Textarea
                id="motif-avoir"
                placeholder="Raison de l'avoir..."
                rows={4}
                value={avoirData.motif}
                onChange={(e) => setAvoirData(prev => ({ ...prev, motif: e.target.value }))}
                data-testid="textarea-motif-avoir"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAvoirDialog(false)}>
              Annuler
            </Button>
            <Button
              onClick={handleGenererAvoir}
              disabled={actionLoading || !avoirData.montant || avoirData.motif.length < 10}
              className="bg-[#FF6200] hover:bg-[#E55900]"
              data-testid="btn-confirm-avoir"
            >
              Générer l'avoir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </DashboardLayout>
  );
}
