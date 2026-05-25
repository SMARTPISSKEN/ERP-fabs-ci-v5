/**
 * API Service for Factures Module
 * Sprint 7
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

// Get all factures with optional filters
export const getFactures = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.type_facture && filters.type_facture !== 'all') params.append('type_facture', filters.type_facture);
  if (filters.statut && filters.statut !== 'all') params.append('statut', filters.statut);
  if (filters.client_id && filters.client_id !== 'all') params.append('client_id', filters.client_id);
  if (filters.date_debut) params.append('date_debut', filters.date_debut);
  if (filters.date_fin) params.append('date_fin', filters.date_fin);
  if (filters.q) params.append('q', filters.q);
  if (filters.skip) params.append('skip', filters.skip);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/factures?${params.toString()}`);
  return response.data;
};

// Get single facture with lignes
export const getFacture = async (factureId) => {
  const response = await axios.get(`${API}/factures/${factureId}`);
  return response.data;
};

// Create new facture
export const createFacture = async (data, type_facture = 'facture') => {
  const response = await axios.post(`${API}/factures?type_facture=${type_facture}`, data);
  return response.data;
};

// Update facture (brouillon only)
export const updateFacture = async (factureId, data) => {
  const response = await axios.patch(`${API}/factures/${factureId}`, data);
  return response.data;
};

// Generate facture from commande
export const generateFactureFromCommande = async (commandeId, dates = {}) => {
  const response = await axios.post(`${API}/factures/generer-depuis-commande`, {
    commande_id: commandeId,
    ...dates,
  });
  return response.data;
};

// Emit facture
export const emettreFacture = async (factureId) => {
  const response = await axios.post(`${API}/factures/${factureId}/emettre`);
  return response.data;
};

// Generate avoir (credit note)
export const genererAvoir = async (factureId, montant, motif) => {
  const response = await axios.post(`${API}/factures/generer-avoir`, {
    facture_id: factureId,
    montant,
    motif,
  });
  return response.data;
};
