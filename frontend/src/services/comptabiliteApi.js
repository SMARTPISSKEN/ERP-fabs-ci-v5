/**
 * API Service for Comptabilité - Sprint 12
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getEcritures = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.journal) params.append('journal', filters.journal);
  if (filters.date_debut) params.append('date_debut', filters.date_debut);
  if (filters.date_fin) params.append('date_fin', filters.date_fin);
  if (filters.limit) params.append('limit', filters.limit);
  
  const response = await axios.get(`${API}/comptabilite/ecritures?${params.toString()}`);
  return response.data;
};

export const createEcriture = async (data) => {
  const response = await axios.post(`${API}/comptabilite/ecritures`, data);
  return response.data;
};

export const getCreances = async () => {
  const response = await axios.get(`${API}/comptabilite/creances`);
  return response.data;
};

export const getBalance = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.date_debut) params.append('date_debut', filters.date_debut);
  if (filters.date_fin) params.append('date_fin', filters.date_fin);
  
  const response = await axios.get(`${API}/comptabilite/balance?${params.toString()}`);
  return response.data;
};
