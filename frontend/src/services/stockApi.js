/**
 * API Service for Stock Module - Sprint 9
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getMouvements = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.produit_id) params.append('produit_id', filters.produit_id);
  if (filters.type_mouvement) params.append('type_mouvement', filters.type_mouvement);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/stock/mouvements?${params.toString()}`);
  return response.data;
};

export const createMouvement = async (data) => {
  const response = await axios.post(`${API}/stock/mouvements`, data);
  return response.data;
};
