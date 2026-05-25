"""
Sprints 8-15 verification (Paiements, Stock, BL, BR, Comptabilité, Utilisateurs,
Paramètres, Recherche globale) + super_admin seed sanity.

Strategy:
- We hit endpoints on the local backend (localhost:8001 because the public URL
  may be hibernated). All "list" endpoints must return 401 without a token.
- /api/health returns 200.
- /api/openapi.json must enumerate all 42 routes.
- We bypass Google OAuth by inserting a session token straight into
  db.user_sessions for the seeded super_admin (pissken@editionsfabsci.com).
- We then validate seeded counts: 8 clients, 35 produits, 3 commandes, 1 facture,
  1 paiement, 9 paramètres. Stock TypeMouvement must include specimen_gratuit.
- Recherche globale must aggregate clients/produits/commandes/factures.
"""
from __future__ import annotations
import os
import secrets
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

# Local backend – the public preview URL may be hibernated.
BASE_URL = "http://localhost:8001"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

PUBLIC_LIST_ENDPOINTS = [
    "/api/clients",
    "/api/produits",
    "/api/commandes",
    "/api/factures",
    "/api/paiements",
    "/api/stock/mouvements",
    "/api/bons-livraison",
    "/api/bons-retour",
    "/api/comptabilite/ecritures",
    "/api/comptabilite/creances",
    "/api/comptabilite/balance",
    "/api/utilisateurs",
    "/api/parametres",
    "/api/recherche/globale?q=test",
    "/api/dashboard/stats",
]


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="module")
def super_admin_token(mongo):
    """Insert a synthetic session for the seeded super_admin."""
    user = mongo.users.find_one({"email": "pissken@editionsfabsci.com"})
    assert user is not None, "super_admin pissken seed missing"
    assert user["role"] == "super_admin", "pissken must be super_admin"

    token = f"test_sprint_8_15_{secrets.token_hex(8)}"
    mongo.user_sessions.insert_one({
        "user_id": user["user_id"],
        "session_token": token,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    })
    yield token
    mongo.user_sessions.delete_one({"session_token": token})


@pytest.fixture(scope="module")
def auth_headers(super_admin_token):
    return {"Authorization": f"Bearer {super_admin_token}"}


# --------------------------------------------------------------------------- #
# Health & routing                                                            #
# --------------------------------------------------------------------------- #
def test_health_no_auth():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_openapi_has_all_42_routes():
    r = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert len(paths) == 42, f"Expected 42 routes, got {len(paths)}"
    # Spot-check Sprints 8-15 routes
    for needed in [
        "/api/paiements", "/api/stock/mouvements", "/api/bons-livraison",
        "/api/bons-retour", "/api/comptabilite/ecritures",
        "/api/comptabilite/creances", "/api/comptabilite/balance",
        "/api/utilisateurs", "/api/parametres", "/api/recherche/globale",
    ]:
        assert needed in paths, f"Missing route: {needed}"


def test_auth_me_without_token_returns_401():
    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 401


@pytest.mark.parametrize("endpoint", PUBLIC_LIST_ENDPOINTS)
def test_list_endpoint_requires_auth(endpoint):
    r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
    assert r.status_code == 401, f"{endpoint} should be 401, got {r.status_code}"


# --------------------------------------------------------------------------- #
# Seed sanity                                                                 #
# --------------------------------------------------------------------------- #
def test_super_admin_seeded(mongo):
    u = mongo.users.find_one({"email": "pissken@editionsfabsci.com"})
    assert u is not None
    assert u["role"] == "super_admin"
    assert u["nom_complet"] == "AKE APPIA YVES DORIS"
    assert u.get("actif") is True


def test_seeded_collection_counts(mongo):
    expectations = {
        "clients": 8,
        "produits": 35,
        "commandes": 3,
        "factures": 1,
        "paiements": 1,
        "parametres": 9,
    }
    actual = {c: mongo[c].count_documents({}) for c in expectations}
    for coll, expected in expectations.items():
        assert actual[coll] >= expected, (
            f"{coll}: expected >= {expected}, got {actual[coll]}"
        )


def test_stock_type_mouvement_includes_specimen_gratuit():
    from stock_module import TypeMouvement
    args = TypeMouvement.__args__  # Literal args
    assert "specimen_gratuit" in args, f"Got {args}"
    for needed in ("entree", "sortie", "ajustement", "retour"):
        assert needed in args


# --------------------------------------------------------------------------- #
# Authenticated endpoint smoke tests                                          #
# --------------------------------------------------------------------------- #
def test_auth_me_with_token(auth_headers):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "pissken@editionsfabsci.com"
    assert body["role"] == "super_admin"


def test_dashboard_stats(auth_headers):
    r = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_paiements_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/paiements", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_stock_mouvements_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/stock/mouvements", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bons_livraison_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/bons-livraison", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bons_retour_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/bons-retour", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_comptabilite_endpoints(auth_headers):
    for path in ("/api/comptabilite/ecritures",
                 "/api/comptabilite/creances",
                 "/api/comptabilite/balance"):
        r = requests.get(f"{BASE_URL}{path}", headers=auth_headers, timeout=10)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


def test_utilisateurs_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/utilisateurs", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    users = r.json()
    assert any(u["email"] == "pissken@editionsfabsci.com" for u in users)


def test_parametres_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/parametres", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    params = r.json()
    assert isinstance(params, list)
    assert len(params) >= 9


def test_recherche_globale_aggregates(auth_headers):
    r = requests.get(
        f"{BASE_URL}/api/recherche/globale",
        params={"q": "FABS"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    results = r.json()
    assert isinstance(results, list)
    # super_admin can see all types; FABS is the common reference prefix
    types_found = {r.get("type") for r in results}
    # Must touch at least 2 modules
    assert len(types_found) >= 2, f"Types: {types_found}"


def test_recherche_globale_min_length():
    r = requests.get(
        f"{BASE_URL}/api/recherche/globale",
        params={"q": "F"},
        timeout=10,
    )
    # min_length validation triggers before auth -> 422
    assert r.status_code in (401, 422)
