/**
 * Service API pour le module Documents AI
 */
import axios from 'axios';

const API = '/api/documents-ai';

export const documentsAiApi = {
  /**
   * Récupérer la liste des documents
   */
  getDocuments: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.type_document) params.append('type_document', filters.type_document);
    if (filters.statut) params.append('statut', filters.statut);
    if (filters.recherche) params.append('recherche', filters.recherche);
    if (filters.page) params.append('page', filters.page);
    if (filters.limit) params.append('limit', filters.limit);

    const response = await axios.get(`${API}?${params.toString()}`);
    return response.data;
  },

  /**
   * Récupérer un document par ID
   */
  getDocument: async (documentId) => {
    const response = await axios.get(`${API}/${documentId}`);
    return response.data;
  },

  /**
   * Créer un nouveau document
   */
  createDocument: async (data) => {
    const response = await axios.post(API, data);
    return response.data;
  },

  /**
   * Mettre à jour un document
   */
  updateDocument: async (documentId, data) => {
    const response = await axios.patch(`${API}/${documentId}`, data);
    return response.data;
  },

  /**
   * Supprimer un document
   */
  deleteDocument: async (documentId) => {
    const response = await axios.delete(`${API}/${documentId}`);
    return response.data;
  },

  /**
   * Récupérer les analytics
   */
  getAnalytics: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.date_debut) params.append('date_debut', filters.date_debut);
    if (filters.date_fin) params.append('date_fin', filters.date_fin);

    const response = await axios.get(`${API}/analytics/dashboard?${params.toString()}`);
    return response.data;
  },

  /**
   * Récupérer les types de documents disponibles
   */
  getTypes: async () => {
    const response = await axios.get(`${API}/meta/types`);
    return response.data;
  },
};
