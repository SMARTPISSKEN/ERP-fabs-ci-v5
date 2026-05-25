import axios from "axios";
import API_BASE_URL from "../config/api";

const API = API_BASE_URL;

/**
 * Récupérer le rapport de ventes avec filtres
 */
export const getRapportVentes = async (filtres = {}) => {
  const params = new URLSearchParams();
  
  if (filtres.matiere) params.append("matiere", filtres.matiere);
  if (filtres.ecole) params.append("ecole", filtres.ecole);
  if (filtres.localite) params.append("localite", filtres.localite);
  if (filtres.niveau_scolaire) params.append("niveau_scolaire", filtres.niveau_scolaire);
  if (filtres.date_debut) params.append("date_debut", filtres.date_debut);
  if (filtres.date_fin) params.append("date_fin", filtres.date_fin);
  
  const r = await axios.get(`${API}/rapports/ventes?${params.toString()}`);
  return r.data;
};

/**
 * Récupérer le rapport de stock
 */
export const getRapportStock = async (filtres = {}) => {
  const params = new URLSearchParams();
  
  if (filtres.matiere) params.append("matiere", filtres.matiere);
  if (filtres.niveau_scolaire) params.append("niveau_scolaire", filtres.niveau_scolaire);
  if (filtres.alerte_uniquement) params.append("alerte_uniquement", "true");
  
  const r = await axios.get(`${API}/rapports/stock?${params.toString()}`);
  return r.data;
};

/**
 * Exporter les données en CSV
 */
export const exportToCSV = (data, filename) => {
  if (!data || data.length === 0) return;
  
  const keys = Object.keys(data[0]);
  const csvContent = [
    keys.join(";"),
    ...data.map(row => keys.map(key => row[key] || "").join(";"))
  ].join("\n");
  
  const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
};

/**
 * Formater un nombre en FCFA
 */
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat("fr-FR").format(amount) + " FCFA";
};
