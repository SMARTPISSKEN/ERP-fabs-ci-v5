/**
 * API Service for Bons de Retour - Sprint 11
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getBonsRetour = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.statut) params.append('statut', filters.statut);
  if (filters.client_id) params.append('client_id', filters.client_id);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/bons-retour?${params.toString()}`);
  return response.data;
};

export const createBonRetour = async (data) => {
  const response = await axios.post(`${API}/bons-retour`, data);
  return response.data;
};

export const validerBonRetour = async (brId) => {
  const response = await axios.post(`${API}/bons-retour/${brId}/valider`);
  return response.data;
};
