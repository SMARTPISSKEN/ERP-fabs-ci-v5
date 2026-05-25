/**
 * ClientPicker — Recherche + sélection + création rapide de client
 * Utilisé dans CommandeForm (étape 1)
 */
import React, { useState, useMemo } from 'react';
import { Search, UserPlus, Check, X, Phone, MapPin } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ScrollArea } from '../ui/scroll-area';
import { createClient } from '../../services/clientsApi';
import { toast } from 'sonner';

const TYPE_OPTIONS = [
  { value: 'ecole', label: 'École' },
  { value: 'librairie', label: 'Librairie' },
  { value: 'particulier', label: 'Particulier' },
  { value: 'distributeur', label: 'Distributeur' },
  { value: 'representant', label: 'Représentant' },
];

const TYPE_COLORS = {
  ecole: 'bg-green-100 text-green-800',
  librairie: 'bg-blue-100 text-blue-800',
  particulier: 'bg-gray-100 text-gray-800',
  distributeur: 'bg-orange-100 text-orange-800',
  representant: 'bg-purple-100 text-purple-800',
};

export default function ClientPicker({ clients, selectedClient, onSelect, onClientCreated }) {
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newClient, setNewClient] = useState({
    nom: '',
    type_client: 'ecole',
    representant: '',
    telephone: '',
    ville: '',
    email: '',
  });

  // Recherche locale dans nom, ville, téléphone, représentant
  const filteredClients = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return clients.slice(0, 50); // Limiter pour perf au démarrage
    return clients
      .filter((c) => {
        const haystack = `${c.nom || ''} ${c.ville || ''} ${c.telephone || ''} ${c.representant || ''} ${c.reference || ''}`.toLowerCase();
        return haystack.includes(q);
      })
      .slice(0, 100);
  }, [clients, search]);

  const handleCreate = async () => {
    if (!newClient.nom.trim() || newClient.nom.length < 2) {
      toast.error('Le nom du client est requis (min 2 caractères)');
      return;
    }
    if (!newClient.representant.trim() || newClient.representant.length < 2) {
      toast.error('Le représentant est requis (min 2 caractères)');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        nom: newClient.nom.trim(),
        type_client: newClient.type_client,
        representant: newClient.representant.trim(),
        telephone: newClient.telephone.trim() || null,
        ville: newClient.ville.trim() || null,
        email: newClient.email.trim() || null,
        plafond_credit: 0,
      };
      const created = await createClient(payload, { force: true });
      toast.success(`Client "${created.nom}" créé`);
      onClientCreated(created);
      onSelect(created.client_id);
      setShowAddModal(false);
      // reset form
      setNewClient({
        nom: '',
        type_client: 'ecole',
        representant: '',
        telephone: '',
        ville: '',
        email: '',
      });
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Erreur lors de la création');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Barre de recherche + bouton ajouter */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <Input
            type="text"
            placeholder="Rechercher par nom, ville, téléphone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="input-search-client"
          />
        </div>
        <Button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="bg-[#FF6200] hover:bg-[#E55900] text-white whitespace-nowrap"
          data-testid="btn-open-add-client"
        >
          <UserPlus className="h-4 w-4 mr-2" />
          Nouveau client
        </Button>
      </div>

      {/* Liste résultats */}
      <div className="border rounded-lg" data-testid="client-list">
        <ScrollArea className="h-72">
          {filteredClients.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">
              {search.trim()
                ? `Aucun client trouvé pour "${search}"`
                : 'Aucun client disponible'}
            </div>
          ) : (
            <ul className="divide-y">
              {filteredClients.map((c) => {
                const isSelected = selectedClient?.client_id === c.client_id;
                return (
                  <li key={c.client_id}>
                    <button
                      type="button"
                      onClick={() => onSelect(c.client_id)}
                      className={`w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex items-start gap-3 ${
                        isSelected ? 'bg-orange-50 dark:bg-orange-900/20' : ''
                      }`}
                      data-testid={`client-row-${c.client_id}`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium truncate">{c.nom}</span>
                          <Badge className={`${TYPE_COLORS[c.type_client] || 'bg-gray-100'} text-xs`}>
                            {c.type_client}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                          <span className="font-mono">{c.reference}</span>
                          {c.ville && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {c.ville}
                            </span>
                          )}
                          {c.telephone && (
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {c.telephone}
                            </span>
                          )}
                          {c.representant && (
                            <span className="truncate">Rep. : {c.representant}</span>
                          )}
                        </div>
                      </div>
                      {isSelected && (
                        <Check className="h-5 w-5 text-[#FF6200] flex-shrink-0 mt-1" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </ScrollArea>
        <div className="px-4 py-2 border-t bg-gray-50 dark:bg-gray-900 text-xs text-gray-500">
          {filteredClients.length} sur {clients.length} clients
          {clients.length > filteredClients.length && ' (filtrés)'}
        </div>
      </div>

      {/* Modale création client */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="sm:max-w-md" data-testid="add-client-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-[#FF6200]" />
              Nouveau client
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div>
              <Label htmlFor="new-nom">Nom *</Label>
              <Input
                id="new-nom"
                value={newClient.nom}
                onChange={(e) => setNewClient({ ...newClient, nom: e.target.value })}
                placeholder="Ex: LYCÉE MODERNE ABIDJAN"
                data-testid="input-new-client-nom"
              />
            </div>

            <div>
              <Label htmlFor="new-type">Type *</Label>
              <Select
                value={newClient.type_client}
                onValueChange={(v) => setNewClient({ ...newClient, type_client: v })}
              >
                <SelectTrigger id="new-type" data-testid="select-new-client-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="new-representant">Représentant *</Label>
              <Input
                id="new-representant"
                value={newClient.representant}
                onChange={(e) => setNewClient({ ...newClient, representant: e.target.value })}
                placeholder="Ex: M. KOUADIO YAO"
                data-testid="input-new-client-representant"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="new-telephone">Téléphone</Label>
                <Input
                  id="new-telephone"
                  value={newClient.telephone}
                  onChange={(e) => setNewClient({ ...newClient, telephone: e.target.value })}
                  placeholder="07 XX XX XX XX"
                  data-testid="input-new-client-telephone"
                />
              </div>
              <div>
                <Label htmlFor="new-ville">Ville</Label>
                <Input
                  id="new-ville"
                  value={newClient.ville}
                  onChange={(e) => setNewClient({ ...newClient, ville: e.target.value })}
                  placeholder="Abidjan"
                  data-testid="input-new-client-ville"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="new-email">Email</Label>
              <Input
                id="new-email"
                type="email"
                value={newClient.email}
                onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                placeholder="contact@exemple.ci"
                data-testid="input-new-client-email"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowAddModal(false)}
              disabled={submitting}
              data-testid="btn-cancel-add-client"
            >
              <X className="h-4 w-4 mr-2" />
              Annuler
            </Button>
            <Button
              type="button"
              onClick={handleCreate}
              disabled={submitting}
              className="bg-[#FF6200] hover:bg-[#E55900]"
              data-testid="btn-submit-new-client"
            >
              <Check className="h-4 w-4 mr-2" />
              {submitting ? 'Création...' : 'Créer et sélectionner'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
