import axios from "axios";

import API_BASE_URL from "../config/api";
const API = API_BASE_URL;

export const CATEGORIES = [
  { value: "maternelle",    label: "Maternelle",     color: "#FFFFFF", bg: "#7C5BC4" },
  { value: "primaire",      label: "Primaire",       color: "#FFFFFF", bg: "#2E7D32" },
  { value: "premier_cycle", label: "Premier cycle",  color: "#FFFFFF", bg: "#0A2540" },
  { value: "second_cycle",  label: "Second cycle",   color: "#FFFFFF", bg: "#FF6200" },
  { value: "litterature",   label: "Littérature",    color: "#FFFFFF", bg: "#C62828" },
];

export const CATEGORIES_MAP = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c])
);

export async function listProducts(params = {}) {
  const r = await axios.get(`${API}/produits`, { params });
  return r.data;
}
export async function getProduct(id) {
  return (await axios.get(`${API}/produits/${id}`)).data;
}
export async function createProduct(payload) {
  return (await axios.post(`${API}/produits`, payload)).data;
}
export async function updateProduct(id, payload) {
  return (await axios.patch(`${API}/produits/${id}`, payload)).data;
}
export async function disableProduct(id) {
  return (await axios.delete(`${API}/produits/${id}`)).data;
}
export async function lookupIsbn(isbn) {
  const r = await axios.get(`${API}/produits/lookup-isbn`, { params: { isbn } });
  return r.data;
}
export async function getStockAlerts() {
  return (await axios.get(`${API}/produits/alertes-stock`)).data;
}
