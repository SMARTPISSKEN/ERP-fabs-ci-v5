"""
EDITIONS FABS-CI ERP — Backend Auth & Profiles tests (Sprint 0 + Sprint 1)
Covers: health endpoints, auth/session, auth/me, auth/logout, /profiles RBAC,
seed idempotency, expired sessions, inactive accounts, CORS, MongoDB _id leakage.
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lovable-editions.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

SUPER_ADMIN_EMAIL = "pissken@editionsfabsci.com"
SUPER_ADMIN_USER_ID = "user_571e26e7609d"
SUPER_ADMIN_TOKEN = "test_super_admin_valid_token"

DG_EMAIL = "ali.mamin@editionsfabsci.com"
DG_USER_ID = "user_de6007be2a72"
DG_TOKEN = "test_dg_valid_token"

EXPIRED_TOKEN = "test_expired_token"


@pytest.fixture(scope="session")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Public endpoints ----------------
class TestPublic:
    def test_root(self, s):
        r = s.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["app"] == "EDITIONS FABS-CI ERP"
        assert data["status"] == "ok"

    def test_health(self, s):
        r = s.get(f"{API}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "time" in data
        # ISO timestamp validation
        from datetime import datetime
        datetime.fromisoformat(data["time"])


# ---------------- /auth/me unauthenticated ----------------
class TestAuthMeUnauthenticated:
    def test_me_no_token(self, s):
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 401
        assert r.json()["detail"] == "Non authentifié"

    def test_me_invalid_token(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer("garbage_token_xyz"))
        assert r.status_code == 401
        assert r.json()["detail"] == "Session invalide"

    def test_me_malformed_authorization(self, s):
        r = s.get(f"{API}/auth/me", headers={"Authorization": "NotBearer xxx"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Non authentifié"


# ---------------- /auth/session ----------------
class TestAuthSession:
    def test_session_missing_session_id(self, s):
        # Empty body -> Pydantic validation error -> 422 expected
        r = s.post(f"{API}/auth/session", json={})
        assert r.status_code in (400, 422), f"got {r.status_code}: {r.text}"

    def test_session_empty_session_id(self, s):
        r = s.post(f"{API}/auth/session", json={"session_id": ""})
        # backend checks `if not payload.session_id` -> 400
        assert r.status_code == 400
        assert "manquant" in r.json()["detail"].lower()

    def test_session_invalid_session_id(self, s):
        r = s.post(f"{API}/auth/session", json={"session_id": "invalid-fake-session-id-xyz"})
        # Emergent provider should reject -> 401 or 502 if unreachable
        assert r.status_code in (401, 502)


# ---------------- Seed profiles ----------------
class TestSeed:
    def test_two_preseed_profiles_exist(self, mongo):
        users = list(mongo.users.find({}, {"_id": 0}))
        emails = sorted([u["email"] for u in users])
        assert SUPER_ADMIN_EMAIL in emails
        assert DG_EMAIL in emails

    def test_super_admin_role(self, mongo):
        u = mongo.users.find_one({"email": SUPER_ADMIN_EMAIL}, {"_id": 0})
        assert u is not None
        assert u["role"] == "super_admin"
        assert u["nom_complet"] == "AKE APPIA YVES DORIS"
        assert u["actif"] is True

    def test_dg_role(self, mongo):
        u = mongo.users.find_one({"email": DG_EMAIL}, {"_id": 0})
        assert u is not None
        assert u["role"] == "directeur_general"
        assert u["nom_complet"] == "ALI MAMIN"

    def test_seed_idempotent_no_duplicates(self, mongo):
        # Count of pre-seeded emails should be exactly one each
        assert mongo.users.count_documents({"email": SUPER_ADMIN_EMAIL}) == 1
        assert mongo.users.count_documents({"email": DG_EMAIL}) == 1


# ---------------- /auth/me authenticated ----------------
class TestAuthMeAuthenticated:
    def test_me_super_admin_valid_token(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == SUPER_ADMIN_EMAIL
        assert data["role"] == "super_admin"
        assert data["nom_complet"] == "AKE APPIA YVES DORIS"
        assert data["actif"] is True
        assert data["user_id"] == SUPER_ADMIN_USER_ID
        # No _id leakage
        assert "_id" not in data

    def test_me_dg_valid_token(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer(DG_TOKEN))
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == DG_EMAIL
        assert data["role"] == "directeur_general"
        assert "_id" not in data

    def test_me_expired_token(self, s):
        r = s.get(f"{API}/auth/me", headers=bearer(EXPIRED_TOKEN))
        assert r.status_code == 401
        assert r.json()["detail"] == "Session expirée"


# ---------------- /profiles RBAC ----------------
class TestProfiles:
    def test_profiles_me_super_admin(self, s):
        r = s.get(f"{API}/profiles/me", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.json()["email"] == SUPER_ADMIN_EMAIL
        assert "_id" not in r.json()

    def test_profiles_me_dg(self, s):
        r = s.get(f"{API}/profiles/me", headers=bearer(DG_TOKEN))
        assert r.status_code == 200
        assert r.json()["email"] == DG_EMAIL

    def test_profiles_list_super_admin(self, s):
        r = s.get(f"{API}/profiles", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        profiles = r.json()
        assert isinstance(profiles, list)
        assert len(profiles) >= 2
        emails = [p["email"] for p in profiles]
        assert SUPER_ADMIN_EMAIL in emails
        assert DG_EMAIL in emails
        # No _id in any profile
        for p in profiles:
            assert "_id" not in p

    def test_profiles_list_forbidden_for_dg(self, s):
        r = s.get(f"{API}/profiles", headers=bearer(DG_TOKEN))
        assert r.status_code == 403
        assert "super administrateur" in r.json()["detail"].lower()

    def test_profiles_list_unauthenticated(self, s):
        r = s.get(f"{API}/profiles")
        assert r.status_code == 401


# ---------------- Inactive account ----------------
class TestInactiveAccount:
    def test_inactive_user_blocked(self, s, mongo):
        # Toggle DG actif=false, hit /auth/me, restore
        try:
            mongo.users.update_one({"email": DG_EMAIL}, {"$set": {"actif": False}})
            r = s.get(f"{API}/auth/me", headers=bearer(DG_TOKEN))
            assert r.status_code == 403
            assert "désactivé" in r.json()["detail"].lower()
        finally:
            mongo.users.update_one({"email": DG_EMAIL}, {"$set": {"actif": True}})


# ---------------- /auth/logout ----------------
class TestLogout:
    def test_logout_deletes_session(self, s, mongo):
        # Create a throwaway session
        throwaway = f"test_logout_{int(time.time()*1000)}"
        from datetime import datetime, timezone, timedelta
        mongo.user_sessions.insert_one({
            "user_id": SUPER_ADMIN_USER_ID,
            "session_token": throwaway,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        })
        # Verify it works
        r = s.get(f"{API}/auth/me", headers=bearer(throwaway))
        assert r.status_code == 200

        # Logout
        r = s.post(f"{API}/auth/logout", headers=bearer(throwaway))
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Token must be invalid now
        r = s.get(f"{API}/auth/me", headers=bearer(throwaway))
        assert r.status_code == 401
        assert r.json()["detail"] == "Session invalide"

        # Confirm DB row gone
        assert mongo.user_sessions.find_one({"session_token": throwaway}) is None

    def test_logout_no_token_idempotent(self, s):
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200


# ---------------- CORS ----------------
class TestCORS:
    def test_cors_preflight_auth_me(self, s):
        r = s.options(
            f"{API}/auth/me",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert r.status_code in (200, 204), r.text
        assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}

    def test_cors_actual_request_has_origin_header(self, s):
        r = s.get(f"{API}/health", headers={"Origin": "https://example.com"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") is not None
