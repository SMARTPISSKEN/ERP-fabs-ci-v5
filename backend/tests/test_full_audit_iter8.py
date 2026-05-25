"""
Audit complet ERP EDITIONS FABS-CI — Iteration 8
Couvre tous les modules + scénario métier E2E.
"""
from __future__ import annotations
import os
import time
import pytest
import requests

BASE_URL = "http://localhost:8001"  # tested locally as recommended by review
API = f"{BASE_URL}/api"

SUPER = ("pissken@editionsfabsci.com", "Admin@2025")
DG = ("ali.mamin@editionsfabsci.com", "DG@2025")


# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture(scope="session")
def super_token():
    r = requests.post(f"{API}/auth/login", json={"email": SUPER[0], "password": SUPER[1]}, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def dg_token():
    r = requests.post(f"{API}/auth/login", json={"email": DG[0], "password": DG[1]}, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def super_h(super_token):
    return {"Authorization": f"Bearer {super_token}"}


@pytest.fixture(scope="session")
def dg_h(dg_token):
    return {"Authorization": f"Bearer {dg_token}"}


# ============================================================================
# AUTH
# ============================================================================
class TestAuth:
    def test_login_super(self):
        r = requests.post(f"{API}/auth/login", json={"email": SUPER[0], "password": SUPER[1]})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and data["user"]["role"] == "super_admin"

    def test_login_dg(self):
        r = requests.post(f"{API}/auth/login", json={"email": DG[0], "password": DG[1]})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "directeur_general"

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": SUPER[0], "password": "WRONG"})
        assert r.status_code == 401

    def test_me_super(self, super_h):
        r = requests.get(f"{API}/auth/me", headers=super_h)
        assert r.status_code == 200
        assert r.json()["email"] == SUPER[0]

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_bad_token(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
        assert r.status_code == 401


# ============================================================================
# SECURITY: 401 sans token sur endpoints protégés
# ============================================================================
PROTECTED_ENDPOINTS = [
    "/clients", "/produits", "/commandes", "/factures", "/paiements",
    "/stock/mouvements", "/bons-livraison", "/bons-retour",
    "/comptabilite/ecritures", "/utilisateurs", "/parametres",
    "/documents-ai", "/analytics/dashboard", "/dashboard/stats",
    "/recherche/globale?q=test",
]


@pytest.mark.parametrize("path", PROTECTED_ENDPOINTS)
def test_security_no_token_returns_401(path):
    r = requests.get(f"{API}{path}")
    assert r.status_code == 401, f"{path} returned {r.status_code} sans Authorization"


# ============================================================================
# DASHBOARD
# ============================================================================
class TestDashboard:
    def test_stats_super(self, super_h):
        r = requests.get(f"{API}/dashboard/stats", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        assert "kpis" in d or "stats" in d or isinstance(d, dict)

    def test_stats_dg(self, dg_h):
        r = requests.get(f"{API}/dashboard/stats", headers=dg_h)
        assert r.status_code == 200


# ============================================================================
# CLIENTS — 419 réels + CRUD
# ============================================================================
class TestClients:
    def test_list_pagination_format(self, super_h):
        r = requests.get(f"{API}/clients?page=1&page_size=10", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        for k in ("items", "total", "page", "page_size"):
            assert k in d, f"missing key {k}"
        assert d["total"] >= 419, f"Expected >=419 real clients, got {d['total']}"

    def test_filter_by_q(self, super_h):
        r = requests.get(f"{API}/clients?q=LIBRAIRIE&page_size=5", headers=super_h)
        assert r.status_code == 200
        assert r.json()["total"] >= 0

    def test_get_by_id_then_404(self, super_h):
        r = requests.get(f"{API}/clients?page_size=1", headers=super_h)
        items = r.json()["items"]
        assert len(items) >= 1
        cid = items[0]["client_id"]
        r2 = requests.get(f"{API}/clients/{cid}", headers=super_h)
        assert r2.status_code == 200
        r3 = requests.get(f"{API}/clients/does_not_exist", headers=super_h)
        assert r3.status_code == 404


# ============================================================================
# PRODUITS — 35 réels + RBAC prix_achat + catégories
# ============================================================================
class TestProduits:
    def test_list_pagination_count(self, super_h):
        r = requests.get(f"{API}/produits?page=1&page_size=100", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d
        assert d["total"] >= 35, f"Expected >=35 real FABS products, got {d['total']}"

    def test_prix_achat_visible_to_super(self, super_h):
        r = requests.get(f"{API}/produits?page_size=5", headers=super_h)
        items = r.json()["items"]
        # at least one product should have prix_achat exposed (not all are 0)
        has_visible = any(i.get("prix_achat") is not None for i in items)
        assert has_visible, "super_admin should see prix_achat (non-null)"

    def test_categorie_literal(self, super_h):
        r = requests.get(f"{API}/produits?page_size=100", headers=super_h)
        items = r.json()["items"]
        allowed = {"maternelle", "primaire", "premier_cycle", "second_cycle", "litterature", "livre_commun"}
        bad = [i for i in items if i.get("categorie") not in allowed]
        assert not bad, f"Found products with unexpected categorie: {[(b['reference'], b['categorie']) for b in bad[:5]]}"

    def test_field_product_id(self, super_h):
        r = requests.get(f"{API}/produits?page_size=5", headers=super_h)
        items = r.json()["items"]
        for it in items:
            assert "product_id" in it, "field must be product_id not produit_id"

    def test_alertes_stock(self, super_h):
        r = requests.get(f"{API}/produits/alertes-stock", headers=super_h)
        assert r.status_code == 200
        # list (route may be plain list)
        d = r.json()
        assert isinstance(d, (list, dict))


# ============================================================================
# PARAMETRES — 9 attendus
# ============================================================================
class TestParametres:
    def test_list(self, super_h):
        r = requests.get(f"{API}/parametres", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        # plain list expected
        assert isinstance(d, list)
        assert len(d) >= 9, f"Expected >=9 parametres, got {len(d)}"


# ============================================================================
# UTILISATEURS — RBAC: PRD dit DG NE DOIT PAS y avoir accès
# ============================================================================
class TestUtilisateursRBAC:
    def test_super_can_list(self, super_h):
        r = requests.get(f"{API}/utilisateurs", headers=super_h)
        assert r.status_code == 200

    def test_dg_should_be_denied_per_prd(self, dg_h):
        """Per PRD le DG ne doit pas voir /api/utilisateurs.
        Si ce test ÉCHOUE (200), il s'agit d'un bug RBAC à corriger."""
        r = requests.get(f"{API}/utilisateurs", headers=dg_h)
        assert r.status_code == 403, (
            f"BUG RBAC: DG a accès à /api/utilisateurs (status={r.status_code}); "
            f"le PRD interdit cet accès. READ_ROLES inclut 'directeur_general' "
            f"dans administration_module.py"
        )


# ============================================================================
# LIST endpoints retour PLAT vs PAGINÉ — vérification du format
# ============================================================================
class TestResponseFormatConsistency:
    """Documente l'incohérence: certains endpoints renvoient une liste plate."""

    PLAIN_LIST = [
        "/commandes", "/factures", "/paiements", "/stock/mouvements",
        "/bons-livraison", "/bons-retour", "/comptabilite/ecritures",
        "/utilisateurs", "/parametres",
    ]
    PAGINATED = ["/clients", "/produits", "/documents-ai"]

    def test_plain_lists(self, super_h):
        for path in self.PLAIN_LIST:
            r = requests.get(f"{API}{path}", headers=super_h)
            assert r.status_code == 200, f"{path} -> {r.status_code}"
            assert isinstance(r.json(), list), f"{path} doit être une liste plate"

    def test_paginated_dicts(self, super_h):
        for path in self.PAGINATED:
            r = requests.get(f"{API}{path}", headers=super_h)
            assert r.status_code == 200, f"{path} -> {r.status_code}"
            d = r.json()
            assert isinstance(d, dict) and "items" in d, f"{path} doit être paginé"


# ============================================================================
# RECHERCHE
# ============================================================================
class TestRecherche:
    def test_recherche_globale(self, super_h):
        r = requests.get(f"{API}/recherche/globale?q=LIBRAIRIE", headers=super_h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ============================================================================
# ANALYTICS
# ============================================================================
class TestAnalytics:
    def test_dashboard(self, super_h):
        r = requests.get(f"{API}/analytics/dashboard", headers=super_h)
        assert r.status_code == 200


# ============================================================================
# DOCUMENTS AI
# ============================================================================
class TestDocumentsAi:
    def test_list_paginated(self, super_h):
        r = requests.get(f"{API}/documents-ai?page=1&page_size=10", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d

    def test_analytics_dashboard(self, super_h):
        r = requests.get(f"{API}/documents-ai/analytics/dashboard", headers=super_h)
        assert r.status_code == 200

    def test_meta_types(self, super_h):
        r = requests.get(f"{API}/documents-ai/meta/types", headers=super_h)
        assert r.status_code == 200


# ============================================================================
# COMPTABILITE
# ============================================================================
class TestComptabilite:
    def test_ecritures(self, super_h):
        r = requests.get(f"{API}/comptabilite/ecritures", headers=super_h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_balance(self, super_h):
        r = requests.get(f"{API}/comptabilite/balance", headers=super_h)
        assert r.status_code == 200


# ============================================================================
# STOCK
# ============================================================================
class TestStock:
    def test_mouvements_list(self, super_h):
        r = requests.get(f"{API}/stock/mouvements", headers=super_h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ============================================================================
# SCÉNARIO MÉTIER E2E
# Client → Commande (2 produits) → Validation → Facture → Paiement partiel
# → Préparation → BL → Livraison (stock -) → Retour partiel (stock +)
# → Analytics
# ============================================================================
@pytest.fixture(scope="session")
def e2e_context(super_h):
    """Pré-fetch un client et 2 produits pour le scénario E2E"""
    # Get first active client
    r = requests.get(f"{API}/clients?page_size=1&actif=true", headers=super_h)
    items = r.json()["items"]
    client_id = items[0]["client_id"]

    # Get 2 active products with stock > 0
    r = requests.get(f"{API}/produits?page_size=100", headers=super_h)
    prods = [p for p in r.json()["items"] if p.get("stock_actuel", 0) > 5 and p.get("actif", True)]
    assert len(prods) >= 2, "Pas assez de produits avec stock pour E2E"
    p1, p2 = prods[0], prods[1]

    return {
        "client_id": client_id,
        "p1": p1,
        "p2": p2,
    }


class TestE2E:
    """Scénario métier complet — exécuté séquentiellement"""

    _state = {}  # shared between tests in this class (session-scoped is class methods)

    def test_01_create_commande_submitted(self, super_h, e2e_context):
        payload = {
            "client_id": e2e_context["client_id"],
            "remise_globale": 0,
            "notes": "TEST_E2E iteration 8",
            "lignes": [
                {"produit_id": e2e_context["p1"]["product_id"], "quantite": 3,
                 "prix_unitaire": e2e_context["p1"]["prix_vente"], "remise_ligne": 0},
                {"produit_id": e2e_context["p2"]["product_id"], "quantite": 2,
                 "prix_unitaire": e2e_context["p2"]["prix_vente"], "remise_ligne": 0},
            ],
        }
        r = requests.post(f"{API}/commandes?submit=true", json=payload, headers=super_h)
        assert r.status_code == 201, r.text
        cmd = r.json()
        assert cmd["statut"] == "en_attente"
        expected_total = (3 * e2e_context["p1"]["prix_vente"] +
                          2 * e2e_context["p2"]["prix_vente"])
        assert abs(cmd["montant_total"] - expected_total) < 1
        TestE2E._state["commande_id"] = cmd["commande_id"]
        TestE2E._state["commande_ref"] = cmd["reference"]
        TestE2E._state["expected_total"] = expected_total
        TestE2E._state["p1_stock_before"] = e2e_context["p1"]["stock_actuel"]
        TestE2E._state["p2_stock_before"] = e2e_context["p2"]["stock_actuel"]
        TestE2E._state["p1_id"] = e2e_context["p1"]["product_id"]
        TestE2E._state["p2_id"] = e2e_context["p2"]["product_id"]
        TestE2E._state["p1_prix"] = e2e_context["p1"]["prix_vente"]
        TestE2E._state["p2_prix"] = e2e_context["p2"]["prix_vente"]
        TestE2E._state["client_id"] = e2e_context["client_id"]

    def test_02_get_commande_lignes(self, super_h):
        cid = TestE2E._state["commande_id"]
        r = requests.get(f"{API}/commandes/{cid}", headers=super_h)
        assert r.status_code == 200
        d = r.json()
        assert len(d["lignes"]) == 2

    def test_03_valider_commande(self, super_h):
        cid = TestE2E._state["commande_id"]
        # Total est probablement < 500k donc commercial/super peut valider
        r = requests.post(f"{API}/commandes/{cid}/valider", headers=super_h)
        assert r.status_code == 200, r.text
        assert r.json()["statut"] == "validee"

    def test_04_facture_auto_or_generate(self, super_h):
        """Après validation, la facture peut être auto-générée; sinon générer manuellement"""
        cid = TestE2E._state["commande_id"]
        # Look for existing
        r = requests.get(f"{API}/factures", headers=super_h)
        existing = [f for f in r.json() if f.get("commande_id") == cid]
        if existing:
            fid = existing[0]["facture_id"]
        else:
            r = requests.post(f"{API}/factures/generer-depuis-commande",
                              json={"commande_id": cid}, headers=super_h)
            assert r.status_code == 201, r.text
            fid = r.json()["facture_id"]
        TestE2E._state["facture_id"] = fid

        # Verify facture details
        r = requests.get(f"{API}/factures/{fid}", headers=super_h)
        assert r.status_code == 200
        f = r.json()
        assert len(f["lignes"]) == 2
        # TVA 18%
        assert abs(f["montant_tva"] - f["montant_ht"] * 0.18) < 1
        TestE2E._state["facture_ttc"] = f["montant_ttc"]

    def test_05_paiement_partiel(self, super_h):
        fid = TestE2E._state["facture_id"]
        ttc = TestE2E._state["facture_ttc"]
        half = round(ttc / 2, 2)
        payload = {
            "client_id": TestE2E._state["client_id"],
            "date_paiement": "2026-01-15",
            "mode_paiement": "especes",
            "montant_total": half,
            "factures": [{"facture_id": fid, "montant_affecte": half}],
            "notes": "TEST_E2E paiement partiel",
        }
        r = requests.post(f"{API}/paiements", json=payload, headers=super_h)
        assert r.status_code == 201, r.text
        # Verify facture restant
        r = requests.get(f"{API}/factures/{fid}", headers=super_h)
        f = r.json()
        assert abs(f["montant_regle"] - half) < 1
        assert abs(f["montant_restant"] - (ttc - half)) < 1

    def test_06_preparer_commande(self, super_h):
        cid = TestE2E._state["commande_id"]
        r = requests.post(f"{API}/commandes/{cid}/preparer", headers=super_h)
        assert r.status_code == 200, r.text
        assert r.json()["statut"] == "preparee"

    def test_07_create_bl_and_livrer_stock_decremented(self, super_h):
        cid = TestE2E._state["commande_id"]
        payload = {
            "commande_id": cid,
            "date_livraison_prevue": "2026-01-20",
            "notes": "TEST_E2E BL",
            "lignes": [
                {"produit_id": TestE2E._state["p1_id"], "quantite": 3},
                {"produit_id": TestE2E._state["p2_id"], "quantite": 2},
            ],
        }
        r = requests.post(f"{API}/bons-livraison", json=payload, headers=super_h)
        assert r.status_code == 201, r.text
        bl_id = r.json()["bl_id"]
        TestE2E._state["bl_id"] = bl_id

        r = requests.post(f"{API}/bons-livraison/{bl_id}/livrer", headers=super_h)
        assert r.status_code == 200, r.text
        assert r.json()["statut"] == "livre"

        # Verify stock decremented
        r = requests.get(f"{API}/produits/{TestE2E._state['p1_id']}", headers=super_h)
        assert r.status_code == 200
        new_stock = r.json()["stock_actuel"]
        assert new_stock == TestE2E._state["p1_stock_before"] - 3, (
            f"Stock p1 attendu {TestE2E._state['p1_stock_before']-3}, obtenu {new_stock}"
        )
        TestE2E._state["p1_stock_after_bl"] = new_stock

    def test_08_create_bon_retour_and_validate_stock_reincremented(self, super_h):
        fid = TestE2E._state["facture_id"]
        payload = {
            "facture_id": fid,
            "client_id": TestE2E._state["client_id"],
            "date_retour": "2026-01-22",
            "motif_global": "TEST_E2E retour partiel pour vérifier ré-entrée stock",
            "lignes": [
                {
                    "produit_id": TestE2E._state["p1_id"],
                    "quantite": 1,
                    "prix_unitaire": TestE2E._state["p1_prix"],
                    "motif": "Test retour partiel iter8",
                },
            ],
        }
        r = requests.post(f"{API}/bons-retour", json=payload, headers=super_h)
        assert r.status_code == 201, r.text
        br_id = r.json()["br_id"]

        r = requests.post(f"{API}/bons-retour/{br_id}/valider", headers=super_h)
        assert r.status_code == 200, r.text
        assert r.json()["statut"] in ("valide", "avoir_genere")

        # Stock should be +1
        r = requests.get(f"{API}/produits/{TestE2E._state['p1_id']}", headers=super_h)
        new_stock = r.json()["stock_actuel"]
        assert new_stock == TestE2E._state["p1_stock_after_bl"] + 1, (
            f"Stock après retour attendu {TestE2E._state['p1_stock_after_bl']+1}, "
            f"obtenu {new_stock}"
        )

    def test_09_analytics_dashboard_responds(self, super_h):
        r = requests.get(f"{API}/analytics/dashboard", headers=super_h)
        assert r.status_code == 200
        # ne pas faire d'assertion sur les chiffres exacts (peut dépendre du seed)

    def test_10_dashboard_stats_responds(self, super_h):
        r = requests.get(f"{API}/dashboard/stats", headers=super_h)
        assert r.status_code == 200
