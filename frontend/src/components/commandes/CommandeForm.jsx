/**
 * Composant de formulaire nouvelle commande - 3 étapes
 * Sprint 6
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Save, Send, Plus, Trash2, Search } from 'lucide-react';
import { createCommande } from '../../services/commandesApi';
import { listClients } from '../../services/clientsApi';
import { listProducts } from '../../services/produitsApi';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Separator } from '../ui/separator';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import DashboardLayout from '../layout/DashboardLayout';

export default function CommandeForm() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [clients, setClients] = useState([]);
  const [produits, setProduits] = useState([]);
  const [searchProduit, setSearchProduit] = useState('');

  const [formData, setFormData] = useState({
    client_id: '',
    date_livraison_prevue: '',
    remise_globale: 0,
    notes: '',
    lignes: [],
  });

  const [selectedClient, setSelectedClient] = useState(null);

  useEffect(() => {
    fetchClients();
    fetchProduits();
  }, []);

  const fetchClients = async () => {
    try {
      const data = await listClients({ actif: true, limit: 200 });
      // Extraire le tableau items de la réponse paginée
      setClients(Array.isArray(data) ? data : (data?.items || []));
    } catch (error) {
      toast.error('Erreur chargement clients');
      setClients([]); // S'assurer que clients reste un tableau
    }
  };

  const fetchProduits = async () => {
    try {
      const data = await listProducts({ actif: true, limit: 200 });
      // Extraire le tableau items de la réponse paginée
      setProduits(Array.isArray(data) ? data : (data?.items || []));
    } catch (error) {
      toast.error('Erreur chargement produits');
      setProduits([]); // S'assurer que produits reste un tableau
    }
  };

  const handleClientSelect = (clientId) => {
    const client = clients.find(c => c.client_id === clientId);
    setSelectedClient(client);
    setFormData(prev => ({ ...prev, client_id: clientId }));
  };

  const addLigne = () => {
    setFormData(prev => ({
      ...prev,
      lignes: [
        ...prev.lignes,
        {
          produit_id: '',
          quantite: 1,
          prix_unitaire: 0,
          remise_ligne: 0,
        }
      ]
    }));
  };

  const removeLigne = (index) => {
    setFormData(prev => ({
      ...prev,
      lignes: prev.lignes.filter((_, i) => i !== index)
    }));
  };

  const updateLigne = (index, field, value) => {
    setFormData(prev => {
      const newLignes = [...prev.lignes];
      newLignes[index][field] = value;

      // Auto-populate prix_unitaire when product is selected
      if (field === 'produit_id') {
        const produit = produits.find(p => p.product_id === value);
        if (produit) {
          newLignes[index].prix_unitaire = produit.prix_vente;
        }
      }

      return { ...prev, lignes: newLignes };
    });
  };

  const calculateMontantLigne = (ligne) => {
    const base = ligne.quantite * ligne.prix_unitaire;
    return base * (1 - ligne.remise_ligne / 100);
  };

  const calculateTotals = () => {
    const montant_ht = formData.lignes.reduce((sum, ligne) => sum + calculateMontantLigne(ligne), 0);
    const montant_remise = montant_ht * (formData.remise_globale / 100);
    const montant_total = montant_ht - montant_remise;
    return { montant_ht, montant_remise, montant_total };
  };

  const validateStep = (stepNum) => {
    if (stepNum === 1) {
      if (!formData.client_id) {
        toast.error('Veuillez sélectionner un client');
        return false;
      }
    }
    if (stepNum === 2) {
      if (formData.lignes.length === 0) {
        toast.error('Veuillez ajouter au moins une ligne');
        return false;
      }
      for (const ligne of formData.lignes) {
        if (!ligne.produit_id || ligne.quantite <= 0 || ligne.prix_unitaire <= 0) {
          toast.error('Veuillez compléter toutes les lignes');
          return false;
        }
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep(step + 1);
    }
  };

  const handlePrev = () => {
    setStep(step - 1);
  };

  const handleSubmit = async (submit = false) => {
    if (!validateStep(2)) return;

    setLoading(true);
    try {
      const commande = await createCommande(formData, submit);
      toast.success(submit ? 'Commande soumise avec succès' : 'Brouillon enregistré');
      navigate(`/commandes/${commande.commande_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + ' FCFA';
  };

  const filteredProduits = Array.isArray(produits) 
    ? produits.filter(p =>
        p.titre?.toLowerCase().includes(searchProduit.toLowerCase()) ||
        p.reference?.toLowerCase().includes(searchProduit.toLowerCase())
      )
    : [];

  const totals = calculateTotals();

  return (
    <DashboardLayout>
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="ghost"
          onClick={() => navigate('/commandes')}
          data-testid="btn-retour"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Retour
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Nouvelle commande</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Étape {step} sur 3</p>
        </div>
      </div>

      {/* Steps Indicator */}
      <div className="flex items-center justify-center mb-8">
        {[1, 2, 3].map((s) => (
          <React.Fragment key={s}>
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                s <= step ? 'bg-[#FF6200] text-white' : 'bg-gray-200 text-gray-600'
              }`}
            >
              {s}
            </div>
            {s < 3 && (
              <div className={`h-1 w-24 ${s < step ? 'bg-[#FF6200]' : 'bg-gray-200'}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Step 1: Select Client */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Sélection du client</CardTitle>
            <CardDescription>Choisissez le client pour cette commande</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="client">Client *</Label>
              <Select
                value={formData.client_id}
                onValueChange={handleClientSelect}
              >
                <SelectTrigger id="client" data-testid="select-client">
                  <SelectValue placeholder="Sélectionnez un client" />
                </SelectTrigger>
                <SelectContent>
                  {Array.isArray(clients) && clients.map((client) => (
                    <SelectItem key={client.client_id} value={client.client_id}>
                      <div>
                        <div className="font-medium">{client.nom}</div>
                        <div className="text-sm text-gray-500">{client.reference}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedClient && (
              <Card className="bg-blue-50 dark:bg-blue-900/20">
                <CardContent className="pt-6">
                  <h4 className="font-semibold mb-2">Informations client</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">Type:</span>{' '}
                      <Badge>{selectedClient.type_client}</Badge>
                    </div>
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">Téléphone:</span>{' '}
                      {selectedClient.telephone}
                    </div>
                    <div className="col-span-2">
                      <span className="text-gray-600 dark:text-gray-400">Email:</span>{' '}
                      {selectedClient.email || '-'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end gap-2 mt-6">
              <Button onClick={handleNext} data-testid="btn-next-step1">
                Suivant <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Add Product Lines */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Lignes de commande</CardTitle>
            <CardDescription>Ajoutez les produits à commander</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={addLigne}
              variant="outline"
              className="w-full"
              data-testid="btn-add-ligne"
            >
              <Plus className="h-4 w-4 mr-2" />
              Ajouter une ligne
            </Button>

            {formData.lignes.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Aucune ligne ajoutée. Cliquez sur "Ajouter une ligne" pour commencer.
              </div>
            ) : (
              <div className="space-y-4">
                {formData.lignes.map((ligne, index) => (
                  <Card key={index} className="bg-gray-50 dark:bg-gray-800">
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-start mb-4">
                        <h4 className="font-semibold">Ligne {index + 1}</h4>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeLigne(index)}
                          data-testid={`btn-remove-ligne-${index}`}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="col-span-2">
                          <Label>Produit *</Label>
                          <Select
                            value={ligne.produit_id}
                            onValueChange={(v) => updateLigne(index, 'produit_id', v)}
                          >
                            <SelectTrigger data-testid={`select-produit-${index}`}>
                              <SelectValue placeholder="Sélectionner" />
                            </SelectTrigger>
                            <SelectContent>
                              {Array.isArray(filteredProduits) && filteredProduits.map((produit) => (
                                <SelectItem key={produit.product_id} value={produit.product_id}>
                                  <div>
                                    <div className="font-medium">{produit.titre}</div>
                                    <div className="text-sm text-gray-500">
                                      {produit.reference} - {formatCurrency(produit.prix_vente)}
                                    </div>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <Label>Quantité *</Label>
                          <Input
                            type="number"
                            min="1"
                            value={ligne.quantite}
                            onChange={(e) => updateLigne(index, 'quantite', parseInt(e.target.value) || 1)}
                            data-testid={`input-quantite-${index}`}
                          />
                        </div>

                        <div>
                          <Label>Prix unitaire *</Label>
                          <Input
                            type="number"
                            min="0"
                            step="100"
                            value={ligne.prix_unitaire}
                            onChange={(e) => updateLigne(index, 'prix_unitaire', parseFloat(e.target.value) || 0)}
                            data-testid={`input-prix-${index}`}
                          />
                        </div>

                        <div>
                          <Label>Remise ligne (%)</Label>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={ligne.remise_ligne}
                            onChange={(e) => updateLigne(index, 'remise_ligne', parseFloat(e.target.value) || 0)}
                            data-testid={`input-remise-ligne-${index}`}
                          />
                        </div>

                        <div className="col-span-3 text-right">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Montant ligne:</span>{' '}
                          <span className="font-semibold text-lg">
                            {formatCurrency(calculateMontantLigne(ligne))}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            <div className="flex justify-between gap-2 mt-6">
              <Button variant="outline" onClick={handlePrev} data-testid="btn-prev-step2">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Précédent
              </Button>
              <Button onClick={handleNext} data-testid="btn-next-step2">
                Suivant <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Résumé et finalisation</CardTitle>
            <CardDescription>Vérifiez les informations avant de soumettre</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Client Info */}
            <div>
              <h4 className="font-semibold mb-2">Client</h4>
              <p className="text-gray-700 dark:text-gray-300">{selectedClient?.nom}</p>
              <p className="text-sm text-gray-500">{selectedClient?.reference}</p>
            </div>

            <Separator />

            {/* Lines Summary */}
            <div>
              <h4 className="font-semibold mb-3">Lignes de commande</h4>
              <div className="space-y-2">
                {formData.lignes.map((ligne, index) => {
                  const produit = produits.find(p => p.product_id === ligne.produit_id);
                  return (
                    <div key={index} className="flex justify-between text-sm">
                      <span>
                        {produit?.titre} x {ligne.quantite}
                        {ligne.remise_ligne > 0 && (
                          <Badge variant="outline" className="ml-2">-{ligne.remise_ligne}%</Badge>
                        )}
                      </span>
                      <span className="font-medium">{formatCurrency(calculateMontantLigne(ligne))}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <Separator />

            {/* Additional Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="date_livraison">Date livraison prévue</Label>
                <Input
                  id="date_livraison"
                  type="date"
                  value={formData.date_livraison_prevue}
                  onChange={(e) => setFormData(prev => ({ ...prev, date_livraison_prevue: e.target.value }))}
                  data-testid="input-date-livraison"
                />
              </div>

              <div>
                <Label htmlFor="remise_globale">Remise globale (%)</Label>
                <Input
                  id="remise_globale"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={formData.remise_globale}
                  onChange={(e) => setFormData(prev => ({ ...prev, remise_globale: parseFloat(e.target.value) || 0 }))}
                  data-testid="input-remise-globale"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Notes internes..."
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                data-testid="textarea-notes"
              />
            </div>

            <Separator />

            {/* Totals */}
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-2">
              <div className="flex justify-between text-sm">
                <span>Sous-total HT:</span>
                <span>{formatCurrency(totals.montant_ht)}</span>
              </div>
              {formData.remise_globale > 0 && (
                <div className="flex justify-between text-sm text-orange-600">
                  <span>Remise globale ({formData.remise_globale}%):</span>
                  <span>-{formatCurrency(totals.montant_remise)}</span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between text-lg font-bold">
                <span>Total:</span>
                <span className="text-[#FF6200]">{formatCurrency(totals.montant_total)}</span>
              </div>
            </div>

            {totals.montant_total > 500000 && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  ⚠️ Cette commande nécessite une validation du Directeur Général (montant &gt; 500 000 FCFA)
                </p>
              </div>
            )}

            <div className="flex justify-between gap-2 mt-6">
              <Button variant="outline" onClick={handlePrev} data-testid="btn-prev-step3">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Précédent
              </Button>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleSubmit(false)}
                  disabled={loading}
                  data-testid="btn-save-draft"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Enregistrer brouillon
                </Button>
                <Button
                  onClick={() => handleSubmit(true)}
                  disabled={loading}
                  className="bg-[#FF6200] hover:bg-[#E55900]"
                  data-testid="btn-submit"
                >
                  <Send className="h-4 w-4 mr-2" />
                  Soumettre
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
    </DashboardLayout>
  );
}
