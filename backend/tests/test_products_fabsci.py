"""
EDITIONS FABS-CI ERP — Sprint 5 Produits tests
Covers /api/produits CRUD, RBAC, prix_achat masking, soft delete,
stock status filtering, reference auto-increment, seed idempotency,
alertes-stock dashboard endpoint, ISBN lookup (Google Books).
"""
import os
import re
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient


def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if url:
        return url.rstrip("/")
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.strip().startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

SUPER_ADMIN_TOKEN = "test_super_admin_valid_token"
DG_TOKEN = "test_dg_valid_token"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def role_tokens(mongo):
    created_users, created_sessions = [], []
    tokens = {"super_admin": SUPER_ADMIN_TOKEN, "directeur_general": DG_TOKEN}
    roles = [
        "comptable", "directeur_commercial", "gestionnaire_stock",
        "responsable_magasinier", "secretariat", "service_logistique",
    ]
    now = datetime.now(timezone.utc)
    for role in roles:
        uid = f"user_test_{uuid.uuid4().hex[:8]}"
        token = f"test_token_prd_{role}_{uuid.uuid4().hex[:6]}"
        mongo.users.insert_one({
            "user_id": uid,
            "email": f"test_prd_{role}_{uuid.uuid4().hex[:6]}@editionsfabsci.com",
            "nom_complet": f"TEST {role}",
            "role": role,
            "actif": True,
            "picture": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        })
        mongo.user_sessions.insert_one({
            "user_id": uid,
            "session_token": token,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
        })
        created_users.append(uid)
        created_sessions.append(token)
        tokens[role] = token
    yield tokens
    mongo.users.delete_many({"user_id": {"$in": created_users}})
    mongo.user_sessions.delete_many({"session_token": {"$in": created_sessions}})


@pytest.fixture(scope="module")
def created_product_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup_created_products(created_product_ids, mongo):
    yield
    if created_product_ids:
        mongo.produits.update_many(
            {"product_id": {"$in": created_product_ids}},
            {"$set": {"actif": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    # Restore DG role just in case
    mongo.users.update_one(
        {"user_id": "user_de6007be2a72"},
        {"$set": {"role": "directeur_general"}},
    )


@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Seed verification ----------------
class TestSeed:
    def test_35_seeded_products(self, mongo):
        count = mongo.produits.count_documents({})
        assert count >= 35, f"expected >=35 seeded products, got {count}"

    def test_seed_references_0001_to_0035(self, mongo):
        refs = sorted(c["reference"] for c in mongo.produits.find(
            {"reference": {"$regex": "^FABS-PRD-00(0[1-9]|[1-2][0-9]|3[0-5])$"}},
            {"_id": 0, "reference": 1}))
        assert refs == [f"FABS-PRD-{i:04d}" for i in range(1, 36)]

    def test_seed_stock_alerts(self, mongo):
        p1 = mongo.produits.find_one({"reference": "FABS-PRD-0001"}, {"_id": 0})
        p28 = mongo.produits.find_one({"reference": "FABS-PRD-0028"}, {"_id": 0})
        assert p1["stock_actuel"] == 3
        assert p28["stock_actuel"] == 0

    def test_counter_at_35(self, mongo):
        c = mongo.counters.find_one({"_id": "produits"})
        assert c and c["seq"] >= 35


# ---------------- Auth ----------------
class TestAuth:
    def test_list_without_auth_401(self, s):
        r = s.get(f"{API}/produits")
        assert r.status_code == 401


# ---------------- RBAC + masking ----------------
class TestRBACList:
    def test_super_admin_sees_prix_achat(self, s):
        r = s.get(f"{API}/produits?page=1&page_size=50", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 35
        # First seeded product has prix_achat=900
        items = {it["reference"]: it for it in data["items"]}
        p1 = items.get("FABS-PRD-0001")
        assert p1 is not None
        assert isinstance(p1["prix_achat"], (int, float))
        assert p1["prix_achat"] > 0

    def test_dg_sees_prix_achat(self, s):
        r = s.get(f"{API}/produits", headers=bearer(DG_TOKEN))
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert isinstance(item["prix_achat"], (int, float))

    def test_commercial_prix_achat_masked(self, s, role_tokens):
        r = s.get(f"{API}/produits", headers=bearer(role_tokens["directeur_commercial"]))
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["prix_achat"] is None

    def test_stock_roles_prix_achat_masked(self, s, role_tokens):
        for role in ["gestionnaire_stock", "responsable_magasinier"]:
            r = s.get(f"{API}/produits", headers=bearer(role_tokens[role]))
            assert r.status_code == 200, role
            for it in r.json()["items"]:
                assert it["prix_achat"] is None, role

    def test_secretariat_forbidden(self, s, role_tokens):
        r = s.get(f"{API}/produits", headers=bearer(role_tokens["secretariat"]))
        assert r.status_code == 403

    def test_logistique_forbidden(self, s, role_tokens):
        r = s.get(f"{API}/produits", headers=bearer(role_tokens["service_logistique"]))
        assert r.status_code == 403

    def test_comptable_forbidden_on_list(self, s, role_tokens):
        r = s.get(f"{API}/produits", headers=bearer(role_tokens["comptable"]))
        assert r.status_code == 403


# ---------------- Filters ----------------
class TestFilters:
    def test_filter_rupture(self, s):
        r = s.get(f"{API}/produits?statut_stock=rupture&page_size=100",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        refs = [it["reference"] for it in items]
        assert "FABS-PRD-0028" in refs
        for it in items:
            assert it["stock_actuel"] <= 0
            assert it["statut_stock"] == "rupture"

    def test_filter_alerte(self, s):
        r = s.get(f"{API}/produits?statut_stock=alerte&page_size=100",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        items = r.json()["items"]
        refs = [it["reference"] for it in items]
        assert "FABS-PRD-0001" in refs
        for it in items:
            assert 0 < it["stock_actuel"] <= it["stock_minimum"]
            assert it["statut_stock"] == "alerte"

    def test_filter_ok(self, s):
        r = s.get(f"{API}/produits?statut_stock=ok&page_size=100",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 33
        for it in items:
            assert it["stock_actuel"] > it["stock_minimum"]

    def test_filter_categorie_maternelle(self, s):
        r = s.get(f"{API}/produits?categorie=maternelle&page=1&page_size=10",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.json()
        # Only consider seeded items in maternelle
        assert data["total"] >= 5
        for it in data["items"]:
            assert it["categorie"] == "maternelle"

    def test_search_q_allah(self, s):
        r = s.get(f"{API}/produits?q=Allah", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        items = r.json()["items"]
        assert any("Allah" in it["titre"] for it in items)

    def test_filter_niveau_terminale(self, s):
        r = s.get(f"{API}/produits?niveau_scolaire=Terminale&page_size=20",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        for it in items:
            assert (it["niveau_scolaire"] or "").lower().startswith("terminale")


# ---------------- Detail ----------------
class TestDetail:
    def test_get_by_id_ok(self, s, mongo):
        prod = mongo.produits.find_one({"reference": "FABS-PRD-0005"}, {"_id": 0})
        r = s.get(f"{API}/produits/{prod['product_id']}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.json()
        assert data["reference"] == "FABS-PRD-0005"
        assert data["statut_stock"] in ("ok", "alerte", "rupture")
        assert isinstance(data["prix_achat"], (int, float))

    def test_get_by_id_404(self, s):
        r = s.get(f"{API}/produits/prd_unknown_xxxx", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 404

    def test_get_by_id_commercial_masked(self, s, mongo, role_tokens):
        prod = mongo.produits.find_one({"reference": "FABS-PRD-0010"}, {"_id": 0})
        r = s.get(f"{API}/produits/{prod['product_id']}",
                  headers=bearer(role_tokens["directeur_commercial"]))
        assert r.status_code == 200
        assert r.json()["prix_achat"] is None


# ---------------- Create / Update / Delete ----------------
class TestCRUD:
    def test_create_super_admin(self, s, created_product_ids):
        payload = {
            "titre": "TEST Produit Pytest 1",
            "auteur": "TEST Auteur",
            "collection": "TEST",
            "categorie": "primaire",
            "niveau_scolaire": "CP1",
            "isbn": "9999000000111",
            "prix_achat": 1000,
            "prix_vente": 2000,
            "stock_actuel": 50,
            "stock_minimum": 10,
        }
        r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 201, r.text
        d = r.json()
        assert re.match(r"^FABS-PRD-\d{4}$", d["reference"])
        assert d["statut_stock"] == "ok"
        assert d["prix_achat"] == 1000
        created_product_ids.append(d["product_id"])

    def test_create_forbidden_roles(self, s, role_tokens):
        payload = {"titre": "TEST x", "categorie": "primaire", "prix_vente": 100}
        for role in ["comptable", "secretariat", "service_logistique"]:
            r = s.post(f"{API}/produits", json=payload, headers=bearer(role_tokens[role]))
            assert r.status_code == 403, role

    def test_create_invalid_prix_vente_zero(self, s):
        payload = {
            "titre": "TEST bad", "categorie": "primaire",
            "prix_achat": 1, "prix_vente": 0,
        }
        r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 422

    def test_reference_increments(self, s, created_product_ids):
        refs = []
        for i in range(3):
            payload = {
                "titre": f"TEST seq {i} {uuid.uuid4().hex[:6]}",
                "categorie": "litterature",
                "prix_achat": 100,
                "prix_vente": 500,
            }
            r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
            assert r.status_code == 201
            d = r.json()
            refs.append(int(d["reference"].split("-")[-1]))
            created_product_ids.append(d["product_id"])
        assert refs[1] == refs[0] + 1
        assert refs[2] == refs[1] + 1

    def test_patch_stock_to_alerte(self, s, role_tokens, created_product_ids):
        # Create one first
        payload = {"titre": "TEST patch stock", "categorie": "primaire",
                   "prix_achat": 100, "prix_vente": 500,
                   "stock_actuel": 50, "stock_minimum": 10}
        r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 201
        pid = r.json()["product_id"]
        created_product_ids.append(pid)
        # Patch as stock manager → 5 < 10 → alerte
        r2 = s.patch(f"{API}/produits/{pid}", json={"stock_actuel": 5},
                     headers=bearer(role_tokens["gestionnaire_stock"]))
        assert r2.status_code == 200, r2.text
        assert r2.json()["statut_stock"] == "alerte"
        assert r2.json()["stock_actuel"] == 5

    def test_patch_empty_body_400(self, s, created_product_ids):
        # Need an id
        payload = {"titre": "TEST empty patch", "categorie": "primaire",
                   "prix_achat": 100, "prix_vente": 500}
        r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
        pid = r.json()["product_id"]
        created_product_ids.append(pid)
        r2 = s.patch(f"{API}/produits/{pid}", json={}, headers=bearer(SUPER_ADMIN_TOKEN))
        assert r2.status_code == 400
        assert "modification" in r2.json().get("detail", "").lower()

    def test_soft_delete_idempotent(self, s, created_product_ids):
        payload = {"titre": "TEST delete", "categorie": "primaire",
                   "prix_achat": 100, "prix_vente": 500}
        r = s.post(f"{API}/produits", json=payload, headers=bearer(SUPER_ADMIN_TOKEN))
        pid = r.json()["product_id"]
        created_product_ids.append(pid)
        r2 = s.delete(f"{API}/produits/{pid}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r2.status_code == 200
        assert r2.json()["actif"] is False
        # Idempotent
        r3 = s.delete(f"{API}/produits/{pid}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r3.status_code == 200
        assert r3.json()["actif"] is False


# ---------------- Alertes Stock ----------------
class TestAlertesStock:
    def test_alertes_stock_super_admin(self, s):
        r = s.get(f"{API}/produits/alertes-stock", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        assert d["rupture"] >= 1
        assert d["alerte"] >= 1
        refs = [it["reference"] for it in d["items"]]
        assert "FABS-PRD-0001" in refs
        assert "FABS-PRD-0028" in refs

    def test_alertes_stock_comptable_allowed(self, s, role_tokens):
        r = s.get(f"{API}/produits/alertes-stock", headers=bearer(role_tokens["comptable"]))
        assert r.status_code == 200

    def test_alertes_stock_secretariat_allowed(self, s, role_tokens):
        r = s.get(f"{API}/produits/alertes-stock", headers=bearer(role_tokens["secretariat"]))
        assert r.status_code == 200


# ---------------- ISBN Lookup ----------------
class TestIsbnLookup:
    def test_lookup_invalid_isbn(self, s):
        r = s.get(f"{API}/produits/lookup-isbn?isbn=ABC", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 400
        assert "ISBN" in r.json().get("detail", "")

    def test_lookup_forbidden_secretariat(self, s, role_tokens):
        r = s.get(f"{API}/produits/lookup-isbn?isbn=9782070612758",
                  headers=bearer(role_tokens["secretariat"]))
        assert r.status_code == 403

    def test_lookup_garbage_not_found(self, s):
        # 13 digits but not a real ISBN
        r = s.get(f"{API}/produits/lookup-isbn?isbn=9999999999999",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        # Network may fail → 200 with found=false; tolerate either real not found
        assert r.status_code == 200
        d = r.json()
        assert d["isbn"] == "9999999999999"
        assert d["found"] is False

    def test_lookup_real_isbn_lenient(self, s):
        # Real ISBN — Google Books may rate-limit, so be lenient
        r = s.get(f"{API}/produits/lookup-isbn?isbn=9782070612758",
                  headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        assert "isbn" in d
        assert "found" in d
        if d["found"] is True:
            assert d.get("titre")
            assert d.get("raw_source") == "google_books"


# ---------------- Regression: prior sprints ----------------
class TestRegression:
    def test_auth_me(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.json()["role"] == "super_admin"

    def test_profiles_list_super_admin(self, s):
        r = s.get(f"{API}/profiles", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_dashboard_stats(self, s):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200

    def test_clients_list(self, s):
        r = s.get(f"{API}/clients", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.json()["total"] >= 8
