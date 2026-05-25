"""
Dashboard demo data — Sprint 3.

These statistics are MOCKED (no real CRUD yet — sprints 4-8 will provide actual
clients/produits/commandes/factures/paiements). Numbers are realistic for an
Ivorian school-book publisher (FCFA, school year 2026-2027). When real modules
land, only this file changes.
"""
from typing import Dict, List

# ---------------------------------------------------------------------------
# KPI definitions per role
# ---------------------------------------------------------------------------
# Each KPI: {key, label, value, suffix, icon, accent, variation_pct}
_ALL_KPIS = {
    "ca_mois": {
        "key": "ca_mois",
        "label": "Chiffre d'affaires du mois",
        "value": 18500000,
        "suffix": "FCFA",
        "icon": "TrendingUp",
        "accent": "#2E7D32",
        "variation_pct": 12.5,
    },
    "factures_impayees": {
        "key": "factures_impayees",
        "label": "Factures impayées",
        "value": 23,
        "suffix": "factures",
        "secondary_value": 7800000,
        "secondary_suffix": "FCFA",
        "icon": "AlertCircle",
        "accent": "#C62828",
        "variation_pct": -3.2,
    },
    "paiements_mois": {
        "key": "paiements_mois",
        "label": "Paiements reçus ce mois",
        "value": 14200000,
        "suffix": "FCFA",
        "icon": "CheckCircle",
        "accent": "#2E7D32",
        "variation_pct": 8.1,
    },
    "commandes_en_cours": {
        "key": "commandes_en_cours",
        "label": "Commandes en cours",
        "value": 47,
        "suffix": "",
        "icon": "ShoppingCart",
        "accent": "#FF6200",
        "variation_pct": 5.0,
    },
    "alertes_stock": {
        "key": "alertes_stock",
        "label": "Alertes stock",
        "value": 8,
        "suffix": "produits",
        "icon": "Package",
        "accent": "#C62828",
        "variation_pct": 0.0,
    },
    "livraisons_jour": {
        "key": "livraisons_jour",
        "label": "Livraisons du jour",
        "value": 12,
        "suffix": "",
        "icon": "Truck",
        "accent": "#0A2540",
        "variation_pct": 2.0,
    },
    "creances_total": {
        "key": "creances_total",
        "label": "Créances clients (total)",
        "value": 7800000,
        "suffix": "FCFA",
        "icon": "Wallet",
        "accent": "#C62828",
        "variation_pct": -1.5,
    },
    "top_clients_count": {
        "key": "top_clients_count",
        "label": "Clients actifs ce mois",
        "value": 34,
        "suffix": "",
        "icon": "Users",
        "accent": "#0A2540",
        "variation_pct": 4.7,
    },
    "ventes_mois": {
        "key": "ventes_mois",
        "label": "Ventes du mois",
        "value": 18500000,
        "suffix": "FCFA",
        "icon": "TrendingUp",
        "accent": "#2E7D32",
        "variation_pct": 12.5,
    },
    "retours_mois": {
        "key": "retours_mois",
        "label": "Retours du mois",
        "value": 4,
        "suffix": "BR",
        "icon": "RotateCcw",
        "accent": "#FF6200",
        "variation_pct": -25.0,
    },
    "mouvements_recents": {
        "key": "mouvements_recents",
        "label": "Mouvements stock (7j)",
        "value": 142,
        "suffix": "",
        "icon": "Activity",
        "accent": "#0A2540",
        "variation_pct": 18.3,
    },
    "ruptures": {
        "key": "ruptures",
        "label": "Produits en rupture",
        "value": 3,
        "suffix": "",
        "icon": "AlertCircle",
        "accent": "#C62828",
        "variation_pct": 50.0,
    },
    "bl_assignes": {
        "key": "bl_assignes",
        "label": "Livraisons assignées",
        "value": 7,
        "suffix": "BL",
        "icon": "Truck",
        "accent": "#0A2540",
        "variation_pct": 0.0,
    },
    "bl_en_route": {
        "key": "bl_en_route",
        "label": "En route",
        "value": 3,
        "suffix": "BL",
        "icon": "Truck",
        "accent": "#FF6200",
        "variation_pct": 0.0,
    },
    "bl_livrees_jour": {
        "key": "bl_livrees_jour",
        "label": "Livrées aujourd'hui",
        "value": 5,
        "suffix": "BL",
        "icon": "CheckCircle",
        "accent": "#2E7D32",
        "variation_pct": 0.0,
    },
}

# Mapping role -> ordered list of KPI keys (max 6 to fit the 4-col grid)
ROLE_KPIS: Dict[str, List[str]] = {
    "super_admin":           ["ca_mois", "factures_impayees", "paiements_mois", "commandes_en_cours", "alertes_stock", "livraisons_jour"],
    "directeur_general":     ["ca_mois", "factures_impayees", "paiements_mois", "commandes_en_cours", "alertes_stock", "livraisons_jour"],
    "comptable":             ["ca_mois", "factures_impayees", "paiements_mois", "creances_total"],
    "directeur_commercial":  ["ventes_mois", "top_clients_count", "commandes_en_cours", "retours_mois"],
    "gestionnaire_stock":    ["alertes_stock", "mouvements_recents", "ruptures", "livraisons_jour"],
    "responsable_magasinier":["alertes_stock", "commandes_en_cours", "ruptures", "livraisons_jour"],
    "secretariat":           ["commandes_en_cours", "top_clients_count"],
    "service_logistique":    ["bl_assignes", "bl_en_route", "bl_livrees_jour"],
}

# Roles that can see graphical charts (CA / catégories / paiements / top clients)
ROLES_WITH_CHARTS = {"super_admin", "directeur_general", "directeur_commercial"}

# Roles that can see paiements pie chart (need payment access)
ROLES_WITH_PAYMENTS_CHART = {"super_admin", "directeur_general", "comptable"}

# Roles that see the Treasury alert (factures access)
ROLES_WITH_TREASURY_ALERT = {"super_admin", "directeur_general", "comptable"}

# ---------------------------------------------------------------------------
# Charts demo data
# ---------------------------------------------------------------------------
VENTES_12_MOIS = [
    {"mois": "Sep 25", "ca": 8200000},
    {"mois": "Oct 25", "ca": 22500000},
    {"mois": "Nov 25", "ca": 14800000},
    {"mois": "Déc 25", "ca": 9300000},
    {"mois": "Jan 26", "ca": 11200000},
    {"mois": "Fév 26", "ca": 13700000},
    {"mois": "Mar 26", "ca": 15900000},
    {"mois": "Avr 26", "ca": 12400000},
    {"mois": "Mai 26", "ca": 18500000},
    {"mois": "Juin 26", "ca": 16100000},
    {"mois": "Juil 26", "ca": 7800000},
    {"mois": "Août 26", "ca": 19200000},
]

VENTES_CATEGORIE = [
    {"categorie": "Maternelle",     "ca": 8400000},
    {"categorie": "Primaire",       "ca": 42500000},
    {"categorie": "Premier cycle",  "ca": 31800000},
    {"categorie": "Second cycle",   "ca": 24300000},
    {"categorie": "Littérature",    "ca": 11200000},
]

PAIEMENTS_MODE = [
    {"mode": "Espèces",       "value": 8400000,  "color": "#0A2540"},
    {"mode": "Mobile Money",  "value": 18900000, "color": "#FF6200"},
    {"mode": "Chèque",        "value": 5200000,  "color": "#C62828"},
    {"mode": "Virement",      "value": 24300000, "color": "#2E7D32"},
]

TOP_CLIENTS = [
    {"nom": "Librairie de France",         "ca": 8500000},
    {"nom": "École La Providence",         "ca": 6200000},
    {"nom": "Distribution Bouaké Centre",  "ca": 5400000},
    {"nom": "Cours Sévigné Abidjan",       "ca": 4900000},
    {"nom": "Librairie Carrefour Cocody",  "ca": 4100000},
]

# ---------------------------------------------------------------------------
# Treasury alert (bonus feature)
# ---------------------------------------------------------------------------
TREASURY_SEUIL_FCFA = 5_000_000
TREASURY_TOTAL_CREANCES = 7_800_000

FACTURES_A_RELANCER = [
    {"reference": "FABS-FC-26-27-0012", "client": "Librairie Carrefour Cocody", "montant": 1_250_000, "jours_retard": 62},
    {"reference": "FABS-FC-26-27-0027", "client": "École La Providence",        "montant": 1_800_000, "jours_retard": 45},
    {"reference": "FABS-FC-26-27-0034", "client": "Distribution Bouaké Centre", "montant": 980_000,   "jours_retard": 31},
    {"reference": "FABS-FC-26-27-0041", "client": "Cours Sévigné Abidjan",      "montant": 720_000,   "jours_retard": 22},
    {"reference": "FABS-FC-26-27-0053", "client": "Lycée Moderne Abobo",        "montant": 1_540_000, "jours_retard": 18},
    {"reference": "FABS-FC-26-27-0061", "client": "Librairie de France",        "montant": 540_000,   "jours_retard": 12},
    {"reference": "FABS-FC-26-27-0068", "client": "Collège Saint-Jean",         "montant": 970_000,   "jours_retard": 8},
]


def build_dashboard_payload(role: str) -> dict:
    """Return a role-tailored stats payload."""
    kpi_keys = ROLE_KPIS.get(role, ["commandes_en_cours"])
    kpis = [_ALL_KPIS[k] for k in kpi_keys]

    charts: dict = {}
    if role in ROLES_WITH_CHARTS:
        charts["ventes_12_mois"] = VENTES_12_MOIS
        charts["ventes_categorie"] = VENTES_CATEGORIE
        charts["top_clients"] = TOP_CLIENTS
    if role in ROLES_WITH_PAYMENTS_CHART:
        charts["paiements_mode"] = PAIEMENTS_MODE

    treasury = None
    if role in ROLES_WITH_TREASURY_ALERT:
        treasury = {
            "seuil_fcfa": TREASURY_SEUIL_FCFA,
            "total_creances": TREASURY_TOTAL_CREANCES,
            "depasse": TREASURY_TOTAL_CREANCES >= TREASURY_SEUIL_FCFA,
            "factures_a_relancer": sorted(
                FACTURES_A_RELANCER, key=lambda f: f["jours_retard"], reverse=True
            ),
        }

    return {
        "role": role,
        "kpis": kpis,
        "charts": charts,
        "treasury_alert": treasury,
        "is_demo_data": True,
    }
