"""
EDITIONS FABS-CI ERP — Sprint 3 Dashboard tests
Covers /api/dashboard/stats:
- Auth gating (401 without Bearer)
- Role-aware KPIs (super_admin, DG, comptable, directeur_commercial,
  gestionnaire_stock, responsable_magasinier, secretariat, service_logistique)
- Charts per role (ventes_12_mois / ventes_categorie / top_clients / paiements_mode)
- Treasury alert (only for SA / DG / comptable), sort order DESC by jours_retard
- is_demo_data flag
- Regression: Sprint 1 endpoints still work
Temporary role users + sessions are created in MongoDB then cleaned up; the
seeded DG user role is NEVER mutated, so credentials in test_credentials.md
remain valid.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if url:
        return url.rstrip("/")
    # Fallback: read frontend/.env (test env doesn't always inherit it)
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

SUPER_ADMIN_TOKEN = "test_super_admin_valid_token"
SUPER_ADMIN_USER_ID = "user_571e26e7609d"
DG_TOKEN = "test_dg_valid_token"
DG_USER_ID = "user_de6007be2a72"

EXPECTED_CHARTS_KEYS = {"ventes_12_mois", "ventes_categorie", "top_clients", "paiements_mode"}
EXPECTED_SORTED_RETARDS = [62, 45, 31, 22, 18, 12, 8]
TREASURY_TOTAL = 7_800_000
TREASURY_SEUIL = 5_000_000

ROLE_EXPECTATIONS = {
    "super_admin": {
        "kpi_keys": ["ca_mois", "factures_impayees", "paiements_mois", "commandes_en_cours", "alertes_stock", "livraisons_jour"],
        "charts": {"ventes_12_mois", "ventes_categorie", "top_clients", "paiements_mode"},
        "treasury": True,
    },
    "directeur_general": {
        "kpi_keys": ["ca_mois", "factures_impayees", "paiements_mois", "commandes_en_cours", "alertes_stock", "livraisons_jour"],
        "charts": {"ventes_12_mois", "ventes_categorie", "top_clients", "paiements_mode"},
        "treasury": True,
    },
    "comptable": {
        "kpi_keys": ["ca_mois", "factures_impayees", "paiements_mois", "creances_total"],
        "charts": {"paiements_mode"},
        "treasury": True,
    },
    "directeur_commercial": {
        "kpi_keys": ["ventes_mois", "top_clients_count", "commandes_en_cours", "retours_mois"],
        "charts": {"ventes_12_mois", "ventes_categorie", "top_clients"},
        "treasury": False,
    },
    "gestionnaire_stock": {
        "kpi_keys": ["alertes_stock", "mouvements_recents", "ruptures", "livraisons_jour"],
        "charts": set(),
        "treasury": False,
    },
    "responsable_magasinier": {
        "kpi_keys": ["alertes_stock", "commandes_en_cours", "ruptures", "livraisons_jour"],
        "charts": set(),
        "treasury": False,
    },
    "secretariat": {
        "kpi_keys": ["commandes_en_cours", "top_clients_count"],
        "charts": set(),
        "treasury": False,
    },
    "service_logistique": {
        "kpi_keys": ["bl_assignes", "bl_en_route", "bl_livrees_jour"],
        "charts": set(),
        "treasury": False,
    },
}


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def role_tokens(mongo):
    """Create one temporary user + session per role we don't already have seeded."""
    created_users = []
    created_sessions = []
    tokens = {
        "super_admin": SUPER_ADMIN_TOKEN,
        "directeur_general": DG_TOKEN,
    }
    roles_to_create = [
        "comptable",
        "directeur_commercial",
        "gestionnaire_stock",
        "responsable_magasinier",
        "secretariat",
        "service_logistique",
    ]
    now = datetime.now(timezone.utc)
    for role in roles_to_create:
        uid = f"user_test_{uuid.uuid4().hex[:8]}"
        email = f"test_{role}_{uuid.uuid4().hex[:6]}@editionsfabsci.com"
        token = f"test_token_{role}_{uuid.uuid4().hex[:8]}"
        mongo.users.insert_one({
            "user_id": uid,
            "email": email,
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

    # Cleanup
    mongo.users.delete_many({"user_id": {"$in": created_users}})
    mongo.user_sessions.delete_many({"session_token": {"$in": created_sessions}})


@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Auth gating ----------------
class TestDashboardAuthGating:
    def test_no_token_returns_401(self, s):
        r = s.get(f"{API}/dashboard/stats")
        assert r.status_code == 401
        assert r.json()["detail"] == "Non authentifié"

    def test_invalid_token_returns_401(self, s):
        r = s.get(f"{API}/dashboard/stats", headers=bearer("garbage_xyz"))
        assert r.status_code == 401


# ---------------- Per-role payload shape ----------------
class TestDashboardPerRole:
    @pytest.mark.parametrize("role", list(ROLE_EXPECTATIONS.keys()))
    def test_role_payload(self, s, role_tokens, role):
        token = role_tokens[role]
        r = s.get(f"{API}/dashboard/stats", headers=bearer(token))
        assert r.status_code == 200, r.text
        data = r.json()

        # Role echoed
        assert data["role"] == role, f"role mismatch for {role}: got {data['role']}"

        # is_demo_data flag
        assert data["is_demo_data"] is True

        # KPI count + keys (ordered)
        exp_keys = ROLE_EXPECTATIONS[role]["kpi_keys"]
        kpis = data["kpis"]
        assert isinstance(kpis, list)
        assert len(kpis) == len(exp_keys), f"{role}: expected {len(exp_keys)} kpis, got {len(kpis)}"
        actual_keys = [k["key"] for k in kpis]
        assert actual_keys == exp_keys, f"{role}: kpi keys mismatch {actual_keys} != {exp_keys}"
        # Each KPI has core fields
        for k in kpis:
            assert "label" in k and "value" in k

        # Charts keys must match exactly
        exp_charts = ROLE_EXPECTATIONS[role]["charts"]
        actual_charts = set(data["charts"].keys())
        assert actual_charts == exp_charts, f"{role}: charts mismatch {actual_charts} != {exp_charts}"

        # Treasury alert presence
        if ROLE_EXPECTATIONS[role]["treasury"]:
            assert data["treasury_alert"] is not None, f"{role}: treasury_alert should be present"
        else:
            assert data["treasury_alert"] is None, f"{role}: treasury_alert should be None"


# ---------------- Charts content sanity ----------------
class TestChartsContent:
    def test_super_admin_has_all_4_charts(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["super_admin"]))
        data = r.json()
        assert set(data["charts"].keys()) == EXPECTED_CHARTS_KEYS
        assert len(data["charts"]["ventes_12_mois"]) == 12
        assert len(data["charts"]["ventes_categorie"]) == 5
        assert len(data["charts"]["top_clients"]) == 5
        assert len(data["charts"]["paiements_mode"]) == 4

    def test_directeur_commercial_no_paiements_mode(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["directeur_commercial"]))
        data = r.json()
        assert "paiements_mode" not in data["charts"]
        assert "ventes_12_mois" in data["charts"]
        assert "ventes_categorie" in data["charts"]
        assert "top_clients" in data["charts"]

    def test_comptable_only_paiements_mode(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["comptable"]))
        data = r.json()
        assert set(data["charts"].keys()) == {"paiements_mode"}


# ---------------- Treasury alert ----------------
class TestTreasuryAlert:
    def test_super_admin_treasury(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["super_admin"]))
        ta = r.json()["treasury_alert"]
        assert ta["seuil_fcfa"] == TREASURY_SEUIL
        assert ta["total_creances"] == TREASURY_TOTAL
        assert ta["depasse"] is True
        assert ta["total_creances"] >= ta["seuil_fcfa"]
        relances = ta["factures_a_relancer"]
        assert len(relances) == 7
        # Sort order DESC by jours_retard
        actual = [f["jours_retard"] for f in relances]
        assert actual == EXPECTED_SORTED_RETARDS, f"sort order wrong: {actual}"
        # Each relance has the required keys
        for f in relances:
            assert "reference" in f and "client" in f and "montant" in f and "jours_retard" in f

    def test_dg_treasury_same_as_super_admin(self, s, role_tokens):
        r1 = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["super_admin"])).json()
        r2 = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["directeur_general"])).json()
        assert r1["treasury_alert"] == r2["treasury_alert"]
        assert r1["kpis"] == r2["kpis"]
        assert r1["charts"] == r2["charts"]

    def test_comptable_treasury_present(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["comptable"]))
        ta = r.json()["treasury_alert"]
        assert ta is not None
        assert ta["depasse"] is True

    def test_directeur_commercial_no_treasury(self, s, role_tokens):
        r = s.get(f"{API}/dashboard/stats", headers=bearer(role_tokens["directeur_commercial"]))
        assert r.json()["treasury_alert"] is None


# ---------------- Sprint 1 Regression ----------------
class TestSprint1Regression:
    def test_auth_me_super_admin(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.json()["role"] == "super_admin"

    def test_auth_me_dg_still_directeur_general(self, s):
        """Critical: ensure no test mutated DG's role."""
        r = s.get(f"{API}/auth/me", headers=bearer(DG_TOKEN))
        assert r.status_code == 200
        assert r.json()["role"] == "directeur_general"
        assert r.json()["email"] == "ali.mamin@editionsfabsci.com"

    def test_profiles_list_super_admin(self, s):
        r = s.get(f"{API}/profiles", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 2

    def test_profiles_me_dg(self, s):
        r = s.get(f"{API}/profiles/me", headers=bearer(DG_TOKEN))
        assert r.status_code == 200
        assert r.json()["role"] == "directeur_general"

    def test_auth_logout_idempotent(self, s):
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------------- Final sanity: DG role restored ----------------
class TestFinalState:
    def test_dg_role_unchanged(self, mongo):
        u = mongo.users.find_one({"email": "ali.mamin@editionsfabsci.com"}, {"_id": 0})
        assert u is not None
        assert u["role"] == "directeur_general", f"DG role drifted to {u['role']}"
        assert u["actif"] is True
