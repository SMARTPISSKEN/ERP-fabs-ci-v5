/**
 * API Service for Bons de Livraison - Sprint 10
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getBonsLivraison = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.statut) params.append('statut', filters.statut);
  if (filters.commande_id) params.append('commande_id', filters.commande_id);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/bons-livraison?${params.toString()}`);
  return response.data;
};

export const createBonLivraison = async (data) => {
  const response = await axios.post(`${API}/bons-livraison`, data);
  return response.data;
};

export const livrerBon = async (blId) => {
  const response = await axios.post(`${API}/bons-livraison/${blId}/livrer`);
  return response.data;
};
