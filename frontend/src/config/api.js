/**
 * Configuration centrale de l'API
 * Utilise des chemins relatifs pour permettre l'accès via Kubernetes Ingress
 */

// L'URL de base de l'API - utilise un chemin relatif
// Le Kubernetes Ingress d'Emergent redirige automatiquement /api vers le backend (port 8001)
export const API_BASE_URL = "/api";

export default API_BASE_URL;
