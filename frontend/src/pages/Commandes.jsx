/**
 * Page Commandes - Liste et gestion des commandes
 * Sprint 6
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Filter, FileText, Calendar, TrendingUp } from 'lucide-react';
import { getCommandes } from '../services/commandesApi';
import { listClients } from '../services/clientsApi';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { toast } from 'sonner';
import { useAuth } from '../hooks/useAuth';
import { can } from '../constants/permissions';
import DashboardLayout from '../components/layout/DashboardLayout';

const STATUT_CONFIG = {
  brouillon: { label: 'Brouillon', color: 'bg-gray-500' },
  en_attente: { label: 'En attente', color: 'bg-yellow-500' },
  validee: { label: 'Validée', color: 'bg-blue-500' },
  preparee: { label: 'Préparée', color: 'bg-purple-500' },
  livree: { label: 'Livrée', color: 'bg-green-500' },
  annulee: { label: 'Annulée', color: 'bg-red-500' },
};

export default function Commandes() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [commandes, setCommandes] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    statut: 'all',
    client_id: 'all',
    q: '',
    date_debut: '',
    date_fin: '',
  });

  const [stats, setStats] = useState({
    total: 0,
    en_attente: 0,
    validees: 0,
    ca_total: 0,
  });

  const canWrite = user && can(user.role, 'commandes', 'create');

  useEffect(() => {
    fetchClients();
    fetchCommandes();
  }, []);

  const fetchClients = async () => {
    try {
      const data = await listClients({ actif: true, page_size: 100 });
      setClients(data.items || []);
    } catch (error) {
      console.error('Erreur chargement clients:', error);
      setClients([]);
    }
  };

  const fetchCommandes = async () => {
    setLoading(true);
    try {
      const data = await getCommandes({ ...filters, limit: 100 });
      setCommandes(data);
      
      // Calculate stats
      const stats = {
        total: data.length,
        en_attente: data.filter(c => c.statut === 'en_attente').length,
        validees: data.filter(c => c.statut === 'validee').length,
        ca_total: data.reduce((sum, c) => sum + (c.statut !== 'annulee' ? c.montant_total : 0), 0),
      };
      setStats(stats);
    } catch (error) {
      console.error('Erreur chargement commandes:', error);
      toast.error('Erreur lors du chargement des commandes');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSearch = () => {
    fetchCommandes();
  };

  const handleReset = () => {
    setFilters({
      statut: 'all',
      client_id: 'all',
      q: '',
      date_debut: '',
      date_fin: '',
    });
    setTimeout(() => fetchCommandes(), 100);
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

  return (
    <DashboardLayout>
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Commandes</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Gestion du cycle de vie des commandes
          </p>
        </div>
        {canWrite && (
          <Button
            onClick={() => navigate('/commandes/nouvelle')}
            className="bg-[#FF6200] hover:bg-[#E55900] text-white"
            data-testid="btn-nouvelle-commande"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nouvelle commande
          </Button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total commandes</CardDescription>
            <CardTitle className="text-2xl">{stats.total}</CardTitle>
          </CardHeader>
          <CardContent>
            <FileText className="h-4 w-4 text-gray-500" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>En attente</CardDescription>
            <CardTitle className="text-2xl text-yellow-600">{stats.en_attente}</CardTitle>
          </CardHeader>
          <CardContent>
            <Calendar className="h-4 w-4 text-yellow-500" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Validées</CardDescription>
            <CardTitle className="text-2xl text-blue-600">{stats.validees}</CardTitle>
          </CardHeader>
          <CardContent>
            <Filter className="h-4 w-4 text-blue-500" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>CA Total</CardDescription>
            <CardTitle className="text-2xl text-green-600">{formatCurrency(stats.ca_total)}</CardTitle>
          </CardHeader>
          <CardContent>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center">
            <Filter className="h-5 w-5 mr-2" />
            Filtres
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Recherche</label>
              <Input
                placeholder="Référence..."
                value={filters.q}
                onChange={(e) => handleFilterChange('q', e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                data-testid="input-search-commande"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Statut</label>
              <Select value={filters.statut} onValueChange={(v) => handleFilterChange('statut', v)}>
                <SelectTrigger data-testid="select-statut">
                  <SelectValue placeholder="Tous" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous</SelectItem>
                  {Object.entries(STATUT_CONFIG).map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Client</label>
              <Select value={filters.client_id} onValueChange={(v) => handleFilterChange('client_id', v)}>
                <SelectTrigger data-testid="select-client">
                  <SelectValue placeholder="Tous" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous</SelectItem>
                  {clients.map((client) => (
                    <SelectItem key={client.client_id} value={client.client_id}>
                      {client.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Date début</label>
              <Input
                type="date"
                value={filters.date_debut}
                onChange={(e) => handleFilterChange('date_debut', e.target.value)}
                data-testid="input-date-debut"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Date fin</label>
              <Input
                type="date"
                value={filters.date_fin}
                onChange={(e) => handleFilterChange('date_fin', e.target.value)}
                data-testid="input-date-fin"
              />
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <Button onClick={handleSearch} data-testid="btn-appliquer-filtres">
              <Search className="h-4 w-4 mr-2" />
              Appliquer
            </Button>
            <Button variant="outline" onClick={handleReset} data-testid="btn-reset-filtres">
              Réinitialiser
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Liste des commandes</CardTitle>
          <CardDescription>{commandes.length} commande(s)</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : commandes.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-400">Aucune commande trouvée</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left">
                    <th className="pb-3 font-semibold">Référence</th>
                    <th className="pb-3 font-semibold">Client</th>
                    <th className="pb-3 font-semibold">Date</th>
                    <th className="pb-3 font-semibold text-right">Montant</th>
                    <th className="pb-3 font-semibold">Statut</th>
                    <th className="pb-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {commandes.map((commande) => (
                    <tr
                      key={commande.commande_id}
                      className="border-b hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                      onClick={() => navigate(`/commandes/${commande.commande_id}`)}
                      data-testid={`row-commande-${commande.reference}`}
                    >
                      <td className="py-3 font-mono text-sm">{commande.reference}</td>
                      <td className="py-3">{commande.client_nom || '-'}</td>
                      <td className="py-3 text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(commande.date_commande)}
                      </td>
                      <td className="py-3 text-right font-semibold">
                        {formatCurrency(commande.montant_total)}
                      </td>
                      <td className="py-3">
                        <Badge className={`${STATUT_CONFIG[commande.statut].color} text-white`}>
                          {STATUT_CONFIG[commande.statut].label}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/commandes/${commande.commande_id}`);
                          }}
                          data-testid={`btn-voir-${commande.reference}`}
                        >
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
    </div>
    </DashboardLayout>
  );
}
