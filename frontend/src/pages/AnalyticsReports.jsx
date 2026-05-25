import { useState, useEffect } from "react";
import axios from "axios";
import {
  TrendingUp,
  DollarSign,
  FileText,
  Users,
  Package,
  BarChart3,
  Download,
  Calendar,
  Filter
} from "lucide-react";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

const API = "/api/analytics";

export default function AnalyticsReports() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [topClients, setTopClients] = useState([]);
  const [topArticles, setTopArticles] = useState([]);
  const [byMatiere, setByMatiere] = useState([]);
  const [byNiveau, setByNiveau] = useState([]);
  const [financial, setFinancial] = useState(null);
  
  // Filtres
  const [filters, setFilters] = useState({
    date_debut: "",
    date_fin: ""
  });

  useEffect(() => {
    fetchAllData();
  }, [filters]);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.date_debut) params.append("date_debut", filters.date_debut);
      if (filters.date_fin) params.append("date_fin", filters.date_fin);
      const queryString = params.toString();

      const [dashRes, clientsRes, articlesRes, matiereRes, niveauRes, finRes] = await Promise.all([
        axios.get(`${API}/dashboard?${queryString}`),
        axios.get(`${API}/top-clients?limit=10&${queryString}`),
        axios.get(`${API}/top-articles?limit=20&${queryString}`),
        axios.get(`${API}/by-matiere?${queryString}`),
        axios.get(`${API}/by-niveau?${queryString}`),
        axios.get(`${API}/financial?${queryString}`)
      ]);

      setDashboard(dashRes.data);
      setTopClients(clientsRes.data.data || []);
      setTopArticles(articlesRes.data.data || []);
      setByMatiere(matiereRes.data.data || []);
      setByNiveau(niveauRes.data.data || []);
      setFinancial(finRes.data);
    } catch (error) {
      console.error("Erreur chargement analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "decimal",
      minimumFractionDigits: 0
    }).format(amount) + " FCFA";
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-screen">
          <p className="text-gray-500">Chargement des rapports...</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">
              Rapports & Analytics
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Analyses complètes des ventes et performances
            </p>
          </div>
          <Button className="bg-[#FF6200] hover:bg-[#E55900] gap-2">
            <Download className="w-4 h-4" />
            Exporter PDF
          </Button>
        </div>

        {/* Filtres */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filtres
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Date début</label>
                <Input
                  type="date"
                  value={filters.date_debut}
                  onChange={(e) => setFilters({...filters, date_debut: e.target.value})}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Date fin</label>
                <Input
                  type="date"
                  value={filters.date_fin}
                  onChange={(e) => setFilters({...filters, date_fin: e.target.value})}
                />
              </div>
              <div className="flex items-end">
                <Button variant="outline" onClick={() => setFilters({date_debut: "", date_fin: ""})}>
                  Réinitialiser
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KPIs Globaux */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">Total Ventes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <TrendingUp className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-2xl font-bold text-[#0A2540]">
                    {formatCurrency(dashboard?.total_ventes || 0)}
                  </p>
                  <p className="text-sm text-gray-500">{dashboard?.total_factures || 0} factures</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">Total TTC</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <DollarSign className="w-8 h-8 text-blue-600" />
                <p className="text-2xl font-bold text-[#0A2540]">
                  {formatCurrency(dashboard?.total_ttc || 0)}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">Clients Actifs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Users className="w-8 h-8 text-purple-600" />
                <p className="text-2xl font-bold text-[#0A2540]">
                  {dashboard?.clients_actifs || 0}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">Quantité Vendue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Package className="w-8 h-8 text-orange-600" />
                <p className="text-2xl font-bold text-[#0A2540]">
                  {dashboard?.quantite_totale || 0}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analyse Financière */}
        {financial && (
          <Card>
            <CardHeader>
              <CardTitle>Analyse Financière</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Total HT</p>
                  <p className="text-xl font-bold">{formatCurrency(financial.total_ht)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Remises</p>
                  <p className="text-xl font-bold text-red-600">{formatCurrency(financial.total_remises)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Encaissé</p>
                  <p className="text-xl font-bold text-green-600">{formatCurrency(financial.total_encaisse)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Restant Dû</p>
                  <p className="text-xl font-bold text-orange-600">{formatCurrency(financial.total_du)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Clients */}
          <Card>
            <CardHeader>
              <CardTitle>Top 10 Clients</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {topClients.map((client, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <p className="font-semibold">{client.client}</p>
                      <p className="text-sm text-gray-600">{client.nb_factures} factures</p>
                    </div>
                    <p className="font-bold text-[#FF6200]">{formatCurrency(client.total_ventes)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Par Catégorie */}
          <Card>
            <CardHeader>
              <CardTitle>Ventes par Catégorie</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {byMatiere.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <p className="font-semibold capitalize">{item.categorie}</p>
                      <p className="text-sm text-gray-600">{item.quantite} unités</p>
                    </div>
                    <p className="font-bold text-blue-600">{formatCurrency(item.total_ventes)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Par Niveau */}
          <Card>
            <CardHeader>
              <CardTitle>Ventes par Niveau</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {byNiveau.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <p className="font-semibold">{item.niveau}</p>
                      <p className="text-sm text-gray-600">{item.quantite} unités</p>
                    </div>
                    <p className="font-bold text-green-600">{formatCurrency(item.total_ventes)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top Articles */}
          <Card>
            <CardHeader>
              <CardTitle>Top 20 Articles Vendus</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {topArticles.map((article, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{article.code_article}</p>
                      <p className="text-xs text-gray-600 truncate">{article.titre}</p>
                    </div>
                    <div className="text-right ml-4">
                      <p className="text-sm font-bold">{article.quantite_vendue} u.</p>
                      <p className="text-xs text-gray-600">{formatCurrency(article.ca_total)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
