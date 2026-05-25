import { useState, useEffect } from "react";
import { BarChart3, Package, Download, FileText, Filter, X, TrendingUp, PieChart, Calendar } from "lucide-react";
import { toast } from "sonner";
import { BarChart, Bar, PieChart as RechartsPie, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import DashboardLayout from "../components/layout/DashboardLayout";
import { getRapportVentes, getRapportStock, exportToCSV, formatCurrency } from "../services/rapportsApi";

const COLORS = ["#FF6200", "#0A2540", "#2E7D32", "#C62828", "#7C3AED", "#F59E0B", "#10B981", "#EF4444"];

export default function Rapports() {
  const [activeTab, setActiveTab] = useState("ventes");
  
  return (
    <DashboardLayout>
      <div className="p-6">
        {/* En-tête */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-8 h-8 text-[#FF6200]" />
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white tracking-tight">
              Rapports & Analyses
            </h1>
          </div>
          <p className="text-sm text-[#0A2540]/60 dark:text-white/60">
            Vue d'ensemble des ventes et du stock avec exports PDF et Excel
          </p>
        </div>

        {/* Onglets */}
        <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-white/10">
          <button
            onClick={() => setActiveTab("ventes")}
            className={`px-4 py-2 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === "ventes"
                ? "border-[#FF6200] text-[#FF6200]"
                : "border-transparent text-[#0A2540]/60 dark:text-white/60 hover:text-[#0A2540] dark:hover:text-white"
            }`}
          >
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Rapports de Ventes
            </div>
          </button>
          <button
            onClick={() => setActiveTab("stock")}
            className={`px-4 py-2 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === "stock"
                ? "border-[#FF6200] text-[#FF6200]"
                : "border-transparent text-[#0A2540]/60 dark:text-white/60 hover:text-[#0A2540] dark:hover:text-white"
            }`}
          >
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              Rapports de Stock
            </div>
          </button>
        </div>

        {/* Contenu */}
        {activeTab === "ventes" ? <RapportVentes /> : <RapportStock />}
      </div>
    </DashboardLayout>
  );
}

// ========== RAPPORT DE VENTES ==========
function RapportVentes() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [filtres, setFiltres] = useState({
    matiere: "",
    ecole: "",
    localite: "",
    niveau_scolaire: "",
    date_debut: "",
    date_fin: "",
  });
  const [showFiltres, setShowFiltres] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await getRapportVentes(filtres);
      setData(result);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur lors du chargement du rapport");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExportCSV = () => {
    if (!data || !data.lignes) return;
    exportToCSV(data.lignes, `rapport_ventes_${new Date().toISOString().split("T")[0]}.csv`);
    toast.success("Export CSV réussi");
  };

  const resetFiltres = () => {
    setFiltres({
      matiere: "",
      ecole: "",
      localite: "",
      niveau_scolaire: "",
      date_debut: "",
      date_fin: "",
    });
  };

  return (
    <div>
      {/* Filtres */}
      <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-[#0A2540] dark:text-white flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filtres
          </h3>
          <button
            onClick={() => setShowFiltres(!showFiltres)}
            className="text-sm text-[#FF6200] hover:underline"
          >
            {showFiltres ? "Masquer" : "Afficher"}
          </button>
        </div>

        {showFiltres && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <input
              type="text"
              placeholder="Matière (ex: Mathématiques)"
              value={filtres.matiere}
              onChange={(e) => setFiltres({ ...filtres, matiere: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
            <input
              type="text"
              placeholder="École"
              value={filtres.ecole}
              onChange={(e) => setFiltres({ ...filtres, ecole: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
            <input
              type="text"
              placeholder="Localité"
              value={filtres.localite}
              onChange={(e) => setFiltres({ ...filtres, localite: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
            <input
              type="text"
              placeholder="Niveau scolaire (ex: CE1)"
              value={filtres.niveau_scolaire}
              onChange={(e) => setFiltres({ ...filtres, niveau_scolaire: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
            <input
              type="date"
              value={filtres.date_debut}
              onChange={(e) => setFiltres({ ...filtres, date_debut: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
            <input
              type="date"
              value={filtres.date_fin}
              onChange={(e) => setFiltres({ ...filtres, date_fin: e.target.value })}
              className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
            />
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-4 py-2 bg-[#FF6200] hover:bg-[#E55900] text-white text-sm font-semibold rounded-lg transition-colors"
          >
            {loading ? "Chargement..." : "Appliquer les filtres"}
          </button>
          <button
            onClick={resetFiltres}
            className="px-4 py-2 bg-gray-200 dark:bg-white/10 hover:bg-gray-300 dark:hover:bg-white/20 text-[#0A2540] dark:text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {data && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Total Quantité</div>
              <div className="text-3xl font-bold text-[#0A2540] dark:text-white">{data.total_quantite}</div>
            </div>
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Montant Total HT</div>
              <div className="text-3xl font-bold text-[#FF6200]">{formatCurrency(data.total_montant)}</div>
            </div>
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Nombre de lignes</div>
              <div className="text-3xl font-bold text-[#0A2540] dark:text-white">{data.nombre_lignes}</div>
            </div>
          </div>

          {/* Boutons Export */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={handleExportCSV}
              className="px-4 py-2 bg-[#2E7D32] hover:bg-[#1B5E20] text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export Excel/CSV
            </button>
            <button
              onClick={() => toast.info("Fonction PDF en développement")}
              className="px-4 py-2 bg-[#C62828] hover:bg-[#B71C1C] text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Export PDF
            </button>
          </div>

          {/* Graphiques */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Graphique à barres - Ventes par matière */}
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <h3 className="font-semibold text-[#0A2540] dark:text-white mb-4">Ventes par Matière</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.agregations.par_matiere}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="matiere" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="montant" fill="#FF6200" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Graphique circulaire - Ventes par localité */}
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <h3 className="font-semibold text-[#0A2540] dark:text-white mb-4">Ventes par Localité</h3>
              <ResponsiveContainer width="100%" height={300}>
                <RechartsPie>
                  <Pie
                    data={data.agregations.par_localite}
                    dataKey="montant"
                    nameKey="localite"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {data.agregations.par_localite.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            </div>

            {/* Courbe d'évolution dans le temps */}
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6 lg:col-span-2">
              <h3 className="font-semibold text-[#0A2540] dark:text-white mb-4">Évolution des Ventes</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data.agregations.par_mois}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mois" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="montant" stroke="#FF6200" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Tableau récapitulatif */}
          <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-[#0A2540] dark:text-white">Détails des Ventes</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-white/5">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Produit</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">École</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Localité</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Niveau</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Quantité</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Montant HT</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lignes.slice(0, 50).map((ligne, idx) => (
                    <tr key={idx} className="border-t border-gray-200 dark:border-white/10">
                      <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white">{ligne.titre_produit}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{ligne.ecole}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{ligne.localite}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{ligne.niveau_scolaire}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white text-right">{ligne.quantite_vendue}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-[#FF6200] text-right">{formatCurrency(ligne.montant_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ========== RAPPORT DE STOCK ==========
function RapportStock() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [filtres, setFiltres] = useState({
    matiere: "",
    niveau_scolaire: "",
    alerte_uniquement: false,
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await getRapportStock(filtres);
      setData(result);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur lors du chargement du rapport");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExportCSV = () => {
    if (!data || !data.produits) return;
    exportToCSV(data.produits, `rapport_stock_${new Date().toISOString().split("T")[0]}.csv`);
    toast.success("Export CSV réussi");
  };

  return (
    <div>
      {/* Filtres */}
      <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-4 mb-6">
        <h3 className="font-semibold text-[#0A2540] dark:text-white mb-4 flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filtres
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <input
            type="text"
            placeholder="Matière"
            value={filtres.matiere}
            onChange={(e) => setFiltres({ ...filtres, matiere: e.target.value })}
            className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
          />
          <input
            type="text"
            placeholder="Niveau scolaire"
            value={filtres.niveau_scolaire}
            onChange={(e) => setFiltres({ ...filtres, niveau_scolaire: e.target.value })}
            className="px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10"
          />
          <label className="flex items-center gap-2 px-3 py-2">
            <input
              type="checkbox"
              checked={filtres.alerte_uniquement}
              onChange={(e) => setFiltres({ ...filtres, alerte_uniquement: e.target.checked })}
              className="w-4 h-4"
            />
            <span className="text-sm text-[#0A2540] dark:text-white">Alertes uniquement</span>
          </label>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-4 py-2 bg-[#FF6200] hover:bg-[#E55900] text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {loading ? "Chargement..." : "Appliquer les filtres"}
        </button>
      </div>

      {data && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Total Produits</div>
              <div className="text-3xl font-bold text-[#0A2540] dark:text-white">{data.total_produits}</div>
            </div>
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Alertes Stock</div>
              <div className="text-3xl font-bold text-[#C62828]">{data.nb_alertes}</div>
            </div>
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 p-6">
              <div className="text-sm text-[#0A2540]/60 dark:text-white/60 mb-1">Valeur Stock Total</div>
              <div className="text-3xl font-bold text-[#2E7D32]">{formatCurrency(data.valeur_stock_total)}</div>
            </div>
          </div>

          {/* Boutons Export */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={handleExportCSV}
              className="px-4 py-2 bg-[#2E7D32] hover:bg-[#1B5E20] text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export Excel/CSV
            </button>
            <button
              onClick={() => toast.info("Fonction PDF en développement")}
              className="px-4 py-2 bg-[#C62828] hover:bg-[#B71C1C] text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Générer PDF
            </button>
          </div>

          {/* Tableau Stock */}
          <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden mb-6">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-[#0A2540] dark:text-white">État du Stock</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-white/5">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Référence</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Désignation</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Niveau</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Stock Actuel</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Stock Min</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Valeur</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {data.produits.map((produit, idx) => (
                    <tr key={idx} className={`border-t border-gray-200 dark:border-white/10 ${produit.en_alerte ? "bg-red-50 dark:bg-red-900/10" : ""}`}>
                      <td className="px-4 py-3 text-sm font-mono text-[#0A2540] dark:text-white">{produit.reference}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white">{produit.titre}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{produit.niveau_scolaire}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white text-right font-semibold">{produit.stock_actuel}</td>
                      <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70 text-right">{produit.stock_minimum}</td>
                      <td className="px-4 py-3 text-sm text-[#2E7D32] text-right font-semibold">{formatCurrency(produit.valeur_stock)}</td>
                      <td className="px-4 py-3 text-center">
                        {produit.statut_stock === "rupture" && (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-500 text-white">Rupture</span>
                        )}
                        {produit.statut_stock === "alerte" && (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-orange-500 text-white">Alerte</span>
                        )}
                        {produit.statut_stock === "ok" && (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-500 text-white">OK</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Historique des mouvements */}
          {data.mouvements_recents && data.mouvements_recents.length > 0 && (
            <div className="bg-white dark:bg-[#0A2540] rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
              <div className="p-4 border-b border-gray-200 dark:border-white/10">
                <h3 className="font-semibold text-[#0A2540] dark:text-white">Mouvements Récents</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-white/5">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Produit</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Type</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Quantité</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#0A2540]/70 dark:text-white/70 uppercase">Motif</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.mouvements_recents.map((mouv, idx) => (
                      <tr key={idx} className="border-t border-gray-200 dark:border-white/10">
                        <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{mouv.date_mouvement?.split("T")[0]}</td>
                        <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white">{mouv.titre_produit}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            mouv.type_mouvement === "entree" ? "bg-green-500 text-white" :
                            mouv.type_mouvement === "sortie" ? "bg-red-500 text-white" :
                            "bg-blue-500 text-white"
                          }`}>
                            {mouv.type_mouvement}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-[#0A2540] dark:text-white text-right font-semibold">{mouv.quantite}</td>
                        <td className="px-4 py-3 text-sm text-[#0A2540]/70 dark:text-white/70">{mouv.motif || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
