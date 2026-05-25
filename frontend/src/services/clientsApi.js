import axios from "axios";

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const TYPE_CLIENTS = [
  { value: "librairie",    label: "Librairie",    color: "#FFFFFF", bg: "#0A2540" },
  { value: "ecole",        label: "École",        color: "#FFFFFF", bg: "#2E7D32" },
  { value: "particulier",  label: "Particulier",  color: "#0A2540", bg: "#E5E7EB" },
  { value: "distributeur", label: "Distributeur", color: "#FFFFFF", bg: "#FF6200" },
  { value: "representant", label: "Représentant", color: "#FFFFFF", bg: "#7C3AED" },
];

export const TYPE_COLOR = Object.fromEntries(
  TYPE_CLIENTS.map((t) => [t.value, t])
);

export async function listClients({ q, type_client, ville, actif, page = 1, page_size = 20 } = {}) {
  const params = { page, page_size };
  if (q) params.q = q;
  if (type_client) params.type_client = type_client;
  if (ville) params.ville = ville;
  if (actif != null) params.actif = actif;
  const r = await axios.get(`${API}/clients`, { params });
  return r.data;
}

export async function getClient(id) {
  const r = await axios.get(`${API}/clients/${id}`);
  return r.data;
}

export async function createClient(payload, { force = false } = {}) {
  const r = await axios.post(`${API}/clients`, payload, { params: { force } });
  return r.data;
}

export async function updateClient(id, payload) {
  const r = await axios.patch(`${API}/clients/${id}`, payload);
  return r.data;
}

export async function disableClient(id) {
  const r = await axios.delete(`${API}/clients/${id}`);
  return r.data;
}

export async function checkDuplicates({ nom, telephone, exclude_id }) {
  const r = await axios.post(`${API}/clients/check-duplicates`, {
    nom,
    telephone: telephone || null,
    exclude_id: exclude_id || null,
  });
  return r.data; // { matches: [...] }
}
