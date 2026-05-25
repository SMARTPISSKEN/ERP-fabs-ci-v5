/**
 * API Service for Paramètres - Sprint 13
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getParametres = async () => {
  const response = await axios.get(`${API}/parametres`);
  return response.data;
};

export const getParametre = async (cle) => {
  const response = await axios.get(`${API}/parametres/${cle}`);
  return response.data;
};

export const updateParametre = async (cle, valeur) => {
  const response = await axios.patch(`${API}/parametres/${cle}`, { valeur });
  return response.data;
};
