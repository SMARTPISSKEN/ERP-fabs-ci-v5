/**
 * API Service for Utilisateurs - Sprint 13
 */
import axios from 'axios';

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const getUtilisateurs = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.actif !== undefined) params.append('actif', filters.actif);
  const response = await axios.get(`${API}/utilisateurs?${params.toString()}`);
  return response.data;
};

export const getUtilisateur = async (userId) => {
  const response = await axios.get(`${API}/utilisateurs/${userId}`);
  return response.data;
};

export const updateUtilisateur = async (userId, data) => {
  const response = await axios.patch(`${API}/utilisateurs/${userId}`, data);
  return response.data;
};

export const deleteUtilisateur = async (userId) => {
  const response = await axios.delete(`${API}/utilisateurs/${userId}`);
  return response.data;
};

// Sprint 13 — Création utilisateur par le super_admin (email + mot de passe)
export const createUtilisateurWithPassword = async ({ email, password, nom_complet, role, actif = true }) => {
  const response = await axios.post(`${API}/auth/create-user`, {
    email,
    password,
    nom_complet,
    role,
    actif,
  });
  return response.data;
};

// Sprint 13 — Réinitialiser mot de passe (super_admin)
export const resetUserPassword = async (userId, newPassword) => {
  const response = await axios.post(`${API}/auth/change-password/${userId}`, {
    new_password: newPassword,
  });
  return response.data;
};
