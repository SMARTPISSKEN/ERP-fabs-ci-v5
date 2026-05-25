// EDITIONS FABS-CI — Matrice d'accès rôle → modules (Sprint 2)
// Conforme au tableau du Sprint 2.

export const MODULES = [
  { key: "dashboard",     path: "/dashboard",     label: "Tableau de bord", icon: "LayoutDashboard" },
  { key: "clients",       path: "/clients",       label: "Clients",         icon: "Users" },
  { key: "produits",      path: "/produits",      label: "Produits",        icon: "BookOpen" },
  { key: "commandes",     path: "/commandes",     label: "Commandes",       icon: "ShoppingCart" },
  { key: "factures",      path: "/factures",      label: "Factures",        icon: "FileText" },
  { key: "paiements",     path: "/paiements",     label: "Paiements",       icon: "CreditCard" },
  { key: "livraisons",    path: "/livraisons",    label: "Livraisons",      icon: "Truck" },
  { key: "retours",       path: "/retours",       label: "Retours",         icon: "RotateCcw" },
  { key: "stock",         path: "/stock",         label: "Stock",           icon: "Package" },
  { key: "comptabilite",  path: "/comptabilite",  label: "Comptabilité",    icon: "Calculator" },
  { key: "rapports",      path: "/rapports",      label: "Rapports",        icon: "BarChart3" },
  { key: "utilisateurs",  path: "/utilisateurs",  label: "Utilisateurs",    icon: "UserCog" },
  { key: "parametres",    path: "/parametres",    label: "Paramètres",      icon: "Settings" },
];

// 1 = autorisé, 0 = refusé
export const PERMISSIONS = {
  // module          : { role: 0|1 }
  dashboard:    { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 1, gestionnaire_stock: 1, responsable_magasinier: 1, secretariat: 1, service_logistique: 1 },
  clients:      { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 1, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 1, service_logistique: 0 },
  produits:     { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 1, gestionnaire_stock: 1, responsable_magasinier: 1, secretariat: 0, service_logistique: 0 },
  commandes:    { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 1, gestionnaire_stock: 0, responsable_magasinier: 1, secretariat: 1, service_logistique: 0 },
  factures:     { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 0, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
  paiements:    { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 0, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
  livraisons:   { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 1, gestionnaire_stock: 1, responsable_magasinier: 1, secretariat: 0, service_logistique: 1 },
  retours:      { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 1, gestionnaire_stock: 1, responsable_magasinier: 1, secretariat: 0, service_logistique: 0 },
  stock:        { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 0, gestionnaire_stock: 1, responsable_magasinier: 1, secretariat: 0, service_logistique: 0 },
  comptabilite: { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 0, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
  rapports:     { super_admin: 1, directeur_general: 1, comptable: 1, directeur_commercial: 1, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
  utilisateurs: { super_admin: 1, directeur_general: 0, comptable: 0, directeur_commercial: 0, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
  parametres:   { super_admin: 1, directeur_general: 1, comptable: 0, directeur_commercial: 0, gestionnaire_stock: 0, responsable_magasinier: 0, secretariat: 0, service_logistique: 0 },
};

export function can(role, moduleKey) {
  if (!role || !moduleKey) return false;
  return PERMISSIONS[moduleKey]?.[role] === 1;
}

export function visibleModulesFor(role) {
  return MODULES.filter((m) => can(role, m.key));
}
