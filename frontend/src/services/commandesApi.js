/**
 * API Service for Commandes Module
 * Sprint 6
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

// Get all commandes with optional filters
export const getCommandes = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.statut && filters.statut !== 'all') params.append('statut', filters.statut);
  if (filters.client_id && filters.client_id !== 'all') params.append('client_id', filters.client_id);
  if (filters.date_debut) params.append('date_debut', filters.date_debut);
  if (filters.date_fin) params.append('date_fin', filters.date_fin);
  if (filters.q) params.append('q', filters.q);
  if (filters.skip) params.append('skip', filters.skip);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/commandes?${params.toString()}`);
  return response.data;
};

// Get single commande with lignes
export const getCommande = async (commandeId) => {
  const response = await axios.get(`${API}/commandes/${commandeId}`);
  return response.data;
};

// Create new commande
export const createCommande = async (data, submit = false) => {
  const response = await axios.post(`${API}/commandes?submit=${submit}`, data);
  return response.data;
};

// Update commande (brouillon only)
export const updateCommande = async (commandeId, data) => {
  const response = await axios.patch(`${API}/commandes/${commandeId}`, data);
  return response.data;
};

// Validate commande
export const validerCommande = async (commandeId) => {
  const response = await axios.post(`${API}/commandes/${commandeId}/valider`);
  return response.data;
};

// Prepare commande
export const preparerCommande = async (commandeId) => {
  const response = await axios.post(`${API}/commandes/${commandeId}/preparer`);
  return response.data;
};

// Deliver commande
export const livrerCommande = async (commandeId) => {
  const response = await axios.post(`${API}/commandes/${commandeId}/livrer`);
  return response.data;
};

// Cancel commande
export const annulerCommande = async (commandeId, motif) => {
  const response = await axios.post(`${API}/commandes/${commandeId}/annuler`, { motif });
  return response.data;
};
