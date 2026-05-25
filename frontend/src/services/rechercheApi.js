/**
 * API Service for Recherche Globale - Sprint 15
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const rechercheGlobale = async (query, limit = 20) => {
  const params = new URLSearchParams();
  params.append('q', query);
  if (limit) params.append('limit', limit);
  
  const response = await axios.get(`${API}/recherche/globale?${params.toString()}`);
  return response.data;
};
