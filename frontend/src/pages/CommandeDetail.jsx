/**
 * Page détail commande avec timeline et actions
 * Sprint 6
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Package, Truck, FileText, AlertCircle } from 'lucide-react';
import {
  getCommande,
  validerCommande,
  preparerCommande,
  livrerCommande,
  annulerCommande,
} from '../services/commandesApi';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Skeleton } from '../components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { useAuth } from '../hooks/useAuth';
import { can } from '../constants/permissions';
import DashboardLayout from '../components/layout/DashboardLayout';
import DocumentActions from '../components/documents/DocumentActions';

const STATUT_CONFIG = {
  brouillon: { label: 'Brouillon', color: 'bg-gray-500', icon: FileText },
  en_attente: { label: 'En attente', color: 'bg-yellow-500', icon: AlertCircle },
  validee: { label: 'Validée', color: 'bg-blue-500', icon: CheckCircle },
  preparee: { label: 'Préparée', color: 'bg-purple-500', icon: Package },
  livree: { label: 'Livrée', color: 'bg-green-500', icon: Truck },
  annulee: { label: 'Annulée', color: 'bg-red-500', icon: XCircle },
};

export default function CommandeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [commande, setCommande] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelMotif, setCancelMotif] = useState('');

  useEffect(() => {
    fetchCommande();
  }, [id]);

  const fetchCommande = async () => {
    setLoading(true);
    try {
      const data = await getCommande(id);
      // S'assurer que les propriétés essentielles sont des tableaux
      const commandeData = {
        ...data,
        lignes: Array.isArray(data?.lignes) ? data.lignes : [],
        historique: Array.isArray(data?.historique) ? data.historique : [],
      };
      setCommande(commandeData);
    } catch (error) {
      toast.error('Erreur lors du chargement de la commande');
      navigate('/commandes');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action, actionFn) => {
    setActionLoading(true);
    try {
      const updated = await actionFn(id);
      // S'assurer que les propriétés essentielles sont des tableaux
      const commandeData = {
        ...updated,
        lignes: Array.isArray(updated?.lignes) ? updated.lignes : [],
        historique: Array.isArray(updated?.historique) ? updated.historique : [],
      };
      setCommande(commandeData);
      toast.success(`Commande ${action} avec succès`);
    } catch (error) {
      toast.error(error.response?.data?.detail || `Erreur lors de l'action: ${action}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!cancelMotif || cancelMotif?.length < 10) {
      toast.error('Veuillez fournir un motif d\'au moins 10 caractères');
      return;
    }
    setActionLoading(true);
    try {
      const updated = await annulerCommande(id, cancelMotif);
      // S'assurer que les propriétés essentielles sont des tableaux
      const commandeData = {
        ...updated,
        lignes: Array.isArray(updated?.lignes) ? updated.lignes : [],
        historique: Array.isArray(updated?.historique) ? updated.historique : [],
      };
      setCommande(commandeData);
      toast.success('Commande annulée');
      setShowCancelDialog(false);
      setCancelMotif('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'annulation');
    } finally {
      setActionLoading(false);
    }
  };

  const canValidate = () => {
    if (!user || !commande) return false;
    if (commande.montant_total > 500000) {
      return user.role === 'super_admin' || user.role === 'directeur_general';
    }
    return ['super_admin', 'directeur_general', 'directeur_commercial'].includes(user.role);
  };

  const canPrepare = () => {
    return user && ['super_admin', 'directeur_general', 'responsable_magasinier'].includes(user.role);
  };

  const canDeliver = () => {
    return user && ['super_admin', 'directeur_general', 'service_logistique'].includes(user.role);
  };

  const canCancelOrder = () => {
    return user && ['super_admin', 'directeur_general', 'directeur_commercial', 'secretariat'].includes(user.role);
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

  if (!commande) return null;

  const StatusIcon = STATUT_CONFIG[commande.statut].icon;

  return (
    <DashboardLayout>
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/commandes')}
            data-testid="btn-retour"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">
              {commande.reference}
            </h1>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={`${STATUT_CONFIG[commande.statut].color} text-white`}>
                {STATUT_CONFIG[commande.statut].label}
              </Badge>
              {commande.montant_total > 500000 && (
                <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                  Validation DG requise
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          <DocumentActions
            pdfUrl={`/api/commandes/${commande.commande_id}/pdf`}
            filename={`${commande.reference}.pdf`}
            phone={commande.client_telephone}
            message={`Bonjour, voici votre bon de commande ${commande.reference}. Merci.`}
            testIdPrefix="commande"
          />
          {commande.statut === 'en_attente' && canValidate() && (
            <Button
              onClick={() => handleAction('validée', validerCommande)}
              disabled={actionLoading}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="btn-valider"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Valider
            </Button>
          )}

          {commande.statut === 'validee' && canPrepare() && (
            <Button
              onClick={() => handleAction('préparée', preparerCommande)}
              disabled={actionLoading}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="btn-preparer"
            >
              <Package className="h-4 w-4 mr-2" />
              Marquer préparée
            </Button>
          )}

          {commande.statut === 'preparee' && canDeliver() && (
            <Button
              onClick={() => handleAction('livrée', livrerCommande)}
              disabled={actionLoading}
              className="bg-green-600 hover:bg-green-700"
              data-testid="btn-livrer"
            >
              <Truck className="h-4 w-4 mr-2" />
              Marquer livrée
            </Button>
          )}

          {!['livree', 'annulee'].includes(commande.statut) && canCancelOrder() && (
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(true)}
              disabled={actionLoading}
              className="text-red-600 border-red-600 hover:bg-red-50"
              data-testid="btn-annuler"
            >
              <XCircle className="h-4 w-4 mr-2" />
              Annuler
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Info */}
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
                  <span className="font-medium">{commande.client_nom || '-'}</span>
                </div>
                <div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">Date commande:</span>{' '}
                  <span className="font-medium">{formatDate(commande.date_commande)}</span>
                </div>
                {commande.date_livraison_prevue && (
                  <div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Livraison prévue:</span>{' '}
                    <span className="font-medium">{formatDate(commande.date_livraison_prevue)}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Lignes */}
          <Card>
            <CardHeader>
              <CardTitle>Lignes de commande</CardTitle>
              <CardDescription>{commande?.lignes?.length || 0} produit(s)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Array.isArray(commande?.lignes) && commande.lignes.map((ligne) => (
                  <div key={ligne.ligne_id} className="flex justify-between items-start border-b pb-3 last:border-0">
                    <div className="flex-1">
                      <div className="font-medium">{ligne.produit_titre || ligne.produit_id}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Réf: {ligne.produit_reference} - Qté: {ligne.quantite} × {formatCurrency(ligne.prix_unitaire)}
                      </div>
                      {ligne.remise_ligne > 0 && (
                        <Badge variant="outline" className="mt-1 text-orange-600">
                          Remise: -{ligne.remise_ligne}%
                        </Badge>
                      )}
                    </div>
                    <div className="font-semibold">
                      {formatCurrency(ligne.montant_ligne)}
                    </div>
                  </div>
                ))}
              </div>

              <Separator className="my-4" />

              {/* Totals */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Sous-total HT:</span>
                  <span>{formatCurrency(commande.montant_ht)}</span>
                </div>
                {commande.remise_globale > 0 && (
                  <div className="flex justify-between text-sm text-orange-600">
                    <span>Remise globale ({commande.remise_globale}%):</span>
                    <span>-{formatCurrency(commande.montant_remise)}</span>
                  </div>
                )}
                <Separator />
                <div className="flex justify-between text-lg font-bold">
                  <span>Total:</span>
                  <span className="text-[#FF6200]">{formatCurrency(commande.montant_total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {commande.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{commande.notes}</p>
              </CardContent>
            </Card>
          )}

          {/* Cancel Reason */}
          {commande.motif_annulation && (
            <Card className="border-red-200 dark:border-red-800">
              <CardHeader>
                <CardTitle className="text-red-600">Motif d'annulation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 dark:text-gray-300">{commande.motif_annulation}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Timeline */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
              <CardDescription>Historique des statuts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Created */}
                <div className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center">
                      <FileText className="h-4 w-4 text-white" />
                    </div>
                    <div className="w-0.5 h-full bg-gray-300 dark:bg-gray-600 mt-2" />
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="font-medium">Créée</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {formatDate(commande.date_commande)}
                    </div>
                  </div>
                </div>

                {/* En attente */}
                {(commande.statut !== 'brouillon') && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-yellow-500 flex items-center justify-center">
                        <AlertCircle className="h-4 w-4 text-white" />
                      </div>
                      {(commande.date_validation || commande.statut === 'en_attente') && (
                        <div className="w-0.5 h-full bg-gray-300 dark:bg-gray-600 mt-2" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="font-medium">En attente validation</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(commande.date_commande)}
                      </div>
                    </div>
                  </div>
                )}

                {/* Validée */}
                {commande.date_validation && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                        <CheckCircle className="h-4 w-4 text-white" />
                      </div>
                      {(commande.date_preparation || ['validee', 'preparee', 'livree'].includes(commande.statut)) && (
                        <div className="w-0.5 h-full bg-gray-300 dark:bg-gray-600 mt-2" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="font-medium">Validée</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(commande.date_validation)}
                      </div>
                    </div>
                  </div>
                )}

                {/* Préparée */}
                {commande.date_preparation && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
                        <Package className="h-4 w-4 text-white" />
                      </div>
                      {(commande.date_livraison || ['preparee', 'livree'].includes(commande.statut)) && (
                        <div className="w-0.5 h-full bg-gray-300 dark:bg-gray-600 mt-2" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="font-medium">Préparée</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(commande.date_preparation)}
                      </div>
                    </div>
                  </div>
                )}

                {/* Livrée */}
                {commande.date_livraison && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                        <Truck className="h-4 w-4 text-white" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">Livrée</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(commande.date_livraison)}
                      </div>
                    </div>
                  </div>
                )}

                {/* Annulée */}
                {commande.statut === 'annulee' && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center">
                        <XCircle className="h-4 w-4 text-white" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">Annulée</div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Cancel Dialog */}
      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Annuler la commande</AlertDialogTitle>
            <AlertDialogDescription>
              Veuillez fournir un motif d'annulation (minimum 10 caractères).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea
            placeholder="Motif d'annulation..."
            value={cancelMotif}
            onChange={(e) => setCancelMotif(e.target.value)}
            rows={4}
            data-testid="textarea-motif-annulation"
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancel}
              disabled={actionLoading || cancelMotif.length < 10}
              className="bg-red-600 hover:bg-red-700"
              data-testid="btn-confirm-annulation"
            >
              Confirmer l'annulation
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </DashboardLayout>
  );
}
