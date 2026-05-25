/**
 * API Service for Paiements Module - Sprint 8
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getPaiements = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.mode_paiement) params.append('mode_paiement', filters.mode_paiement);
  if (filters.client_id) params.append('client_id', filters.client_id);
  if (filters.date_debut) params.append('date_debut', filters.date_debut);
  if (filters.date_fin) params.append('date_fin', filters.date_fin);
  if (filters.q) params.append('q', filters.q);
  
  const response = await axios.get(`${API}/paiements?${params.toString()}`);
  return response.data;
};

export const getPaiement = async (paiementId) => {
  const response = await axios.get(`${API}/paiements/${paiementId}`);
  return response.data;
};

export const createPaiement = async (data) => {
  const response = await axios.post(`${API}/paiements`, data);
  return response.data;
};

export const getPaiementsByFacture = async (factureId) => {
  const response = await axios.get(`${API}/paiements/facture/${factureId}`);
  return response.data;
};
