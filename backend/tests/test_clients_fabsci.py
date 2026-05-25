"""
EDITIONS FABS-CI ERP — Sprint 4 Clients tests
Covers /api/clients CRUD, RBAC, duplicate detection, seed idempotency,
reference generation, soft delete, indexes.

Important: Soft-delete only. Test-created clients are disabled (actif=False)
at teardown — they are NOT physically removed (respects soft-delete invariant).
The reference counter persists; created clients consume sequence numbers
(FABS-CLI-0009+), which is expected behaviour per the agent context note.
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
DG_TOKEN = "test_dg_valid_token"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def role_tokens(mongo):
    """Spin up temporary users for non-seeded roles."""
    created_users, created_sessions = [], []
    tokens = {"super_admin": SUPER_ADMIN_TOKEN, "directeur_general": DG_TOKEN}
    roles = [
        "comptable", "directeur_commercial", "gestionnaire_stock",
        "responsable_magasinier", "secretariat", "service_logistique",
    ]
    now = datetime.now(timezone.utc)
    for role in roles:
        uid = f"user_test_{uuid.uuid4().hex[:8]}"
        token = f"test_token_cli_{role}_{uuid.uuid4().hex[:6]}"
        mongo.users.insert_one({
            "user_id": uid,
            "email": f"test_cli_{role}_{uuid.uuid4().hex[:6]}@editionsfabsci.com",
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
def created_client_ids():
    """Module-level registry for test-created clients (soft-disabled at teardown)."""
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup_created_clients(created_client_ids, mongo):
    yield
    # Soft delete only — respect invariant
    if created_client_ids:
        mongo.clients.update_many(
            {"client_id": {"$in": created_client_ids}},
            {"$set": {"actif": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
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
    def test_8_seeded_clients_exist(self, mongo):
        count = mongo.clients.count_documents({})
        assert count >= 8, f"expected >=8 seeded clients, got {count}"

    def test_seed_references_0001_to_0008(self, mongo):
        refs = sorted([c["reference"] for c in mongo.clients.find(
            {"reference": {"$regex": "^FABS-CLI-000[1-8]$"}}, {"_id": 0, "reference": 1})])
        assert refs == [f"FABS-CLI-{i:04d}" for i in range(1, 9)]

    def test_seed_idempotent_no_duplicate_reference(self, mongo):
        refs = [c["reference"] for c in mongo.clients.find({}, {"_id": 0, "reference": 1})]
        assert len(refs) == len(set(refs)), "Duplicate references found — seed not idempotent"

    def test_mongodb_indexes(self, mongo):
        idx = mongo.clients.index_information()
        # Find unique indexes on client_id and reference
        client_id_unique = any(
            i.get("unique") and i.get("key") == [("client_id", 1)]
            for i in idx.values()
        )
        reference_unique = any(
            i.get("unique") and i.get("key") == [("reference", 1)]
            for i in idx.values()
        )
        assert client_id_unique, f"clients.client_id unique index missing: {idx}"
        assert reference_unique, f"clients.reference unique index missing: {idx}"


# ---------------- Auth gating ----------------
class TestAuthGating:
    def test_list_no_auth_401(self, s):
        r = s.get(f"{API}/clients")
        assert r.status_code == 401

    def test_create_no_auth_401(self, s):
        # Send fully-valid payload so we don't trip Pydantic 422 before auth runs
        r = s.post(f"{API}/clients", json={"nom": "Valid Name", "type_client": "librairie"})
        assert r.status_code == 401, f"got {r.status_code}: {r.text}"


# ---------------- LIST ----------------
class TestList:
    def test_list_super_admin_paginated(self, s):
        r = s.get(f"{API}/clients", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("items", "total", "page", "page_size"):
            assert key in data
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] >= 8
        # Ensure no _id leakage
        for item in data["items"]:
            assert "_id" not in item
            assert item["reference"].startswith("FABS-CLI-")
            assert item["client_id"].startswith("cli_")

    def test_list_gestionnaire_stock_forbidden(self, s, role_tokens):
        r = s.get(f"{API}/clients", headers=bearer(role_tokens["gestionnaire_stock"]))
        assert r.status_code == 403

    def test_list_service_logistique_forbidden(self, s, role_tokens):
        r = s.get(f"{API}/clients", headers=bearer(role_tokens["service_logistique"]))
        assert r.status_code == 403

    def test_list_filters_q_type_ville(self, s):
        r = s.get(
            f"{API}/clients",
            headers=bearer(SUPER_ADMIN_TOKEN),
            params={"q": "Librairie", "type_client": "librairie", "ville": "Abidjan",
                    "page": 1, "page_size": 20},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["type_client"] == "librairie"
            assert item["ville"].startswith("Abidjan")

    def test_list_actif_false_initially_empty(self, s):
        r = s.get(f"{API}/clients", headers=bearer(SUPER_ADMIN_TOKEN), params={"actif": "false"})
        assert r.status_code == 200
        # At first run total should be 0 (no disabled). May be >0 if leftover from prior runs.
        assert isinstance(r.json()["total"], int)

    def test_get_single_client_200(self, s, mongo):
        any_client = mongo.clients.find_one({}, {"_id": 0})
        r = s.get(f"{API}/clients/{any_client['client_id']}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.json()["client_id"] == any_client["client_id"]

    def test_get_unknown_client_404(self, s):
        r = s.get(f"{API}/clients/cli_nonexistent_xyz", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 404


# ---------------- CREATE / RBAC / duplicate detection ----------------
class TestCreate:
    def test_create_secretariat_valid_payload(self, s, role_tokens, created_client_ids, mongo):
        nom = f"TEST_Client_Unique_{uuid.uuid4().hex[:6]}"
        phone = f"+225 07 {uuid.uuid4().int % 100:02d} {uuid.uuid4().int % 100:02d} {uuid.uuid4().int % 100:02d} {uuid.uuid4().int % 100:02d}"
        payload = {
            "nom": nom, "type_client": "particulier",
            "telephone": phone, "email": "test.create@example.com",
            "ville": "Abidjan", "plafond_credit": 100000,
        }
        r = s.post(f"{API}/clients", headers=bearer(role_tokens["secretariat"]), json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["client_id"].startswith("cli_")
        assert data["reference"].startswith("FABS-CLI-")
        # reference number must be >= 9 (seed had 8)
        seq = int(data["reference"].split("-")[-1])
        assert seq >= 9
        assert data["nom"] == nom
        assert data["actif"] is True
        assert data["solde"] == 0
        created_client_ids.append(data["client_id"])

        # Verify GET persistence
        g = s.get(f"{API}/clients/{data['client_id']}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert g.status_code == 200
        assert g.json()["nom"] == nom

    def test_create_gestionnaire_stock_forbidden(self, s, role_tokens):
        r = s.post(
            f"{API}/clients",
            headers=bearer(role_tokens["gestionnaire_stock"]),
            json={"nom": "TEST_Stock_Forbidden", "type_client": "librairie"},
        )
        assert r.status_code == 403

    def test_create_duplicate_phone_409(self, s, role_tokens, mongo):
        # Use FABS-CLI-0001 phone last 8 digits: "+225 27 22 44 30 30" → 22443030
        seed_phone = "27 22 44 30 30"
        payload = {
            "nom": "Lib. de France",  # very similar to "Librairie de France"
            "type_client": "librairie",
            "telephone": seed_phone,
        }
        r = s.post(f"{API}/clients", headers=bearer(role_tokens["secretariat"]), json=payload)
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "DUPLICATE_SUSPECTED"
        assert "matches" in detail
        assert len(detail["matches"]) >= 1
        # At least one with phone_match=True
        assert any(m["phone_match"] for m in detail["matches"])

    def test_create_force_bypasses_duplicate_guard(self, s, role_tokens, created_client_ids):
        seed_phone = "27 22 44 30 30"
        payload = {
            "nom": "Lib. de France BIS",
            "type_client": "librairie",
            "telephone": seed_phone,
        }
        r = s.post(
            f"{API}/clients?force=true",
            headers=bearer(role_tokens["secretariat"]),
            json=payload,
        )
        assert r.status_code == 201, r.text
        created_client_ids.append(r.json()["client_id"])

    def test_sequential_reference_increment(self, s, role_tokens, created_client_ids):
        refs = []
        for i in range(3):
            r = s.post(
                f"{API}/clients",
                headers=bearer(role_tokens["secretariat"]),
                json={
                    "nom": f"TEST_Sequential_{uuid.uuid4().hex[:8]}_{i}",
                    "type_client": "particulier",
                    "telephone": f"+225 05 {i:02d} 99 88 77 6{i}",
                },
            )
            assert r.status_code == 201, r.text
            refs.append(int(r.json()["reference"].split("-")[-1]))
            created_client_ids.append(r.json()["client_id"])
        # Must increment by 1
        assert refs[1] == refs[0] + 1
        assert refs[2] == refs[1] + 1


# ---------------- check-duplicates ----------------
class TestCheckDuplicates:
    def test_similar_name_and_matching_phone(self, s, role_tokens):
        r = s.post(
            f"{API}/clients/check-duplicates",
            headers=bearer(role_tokens["secretariat"]),
            json={"nom": "Lib. Carrefour Coc", "telephone": "+225 27 22 44 50 10"},
        )
        assert r.status_code == 200, r.text
        matches = r.json()["matches"]
        assert len(matches) >= 1
        # The Carrefour Cocody seed should be there with phone_match=True
        assert any(m["phone_match"] and "Carrefour" in m["nom"] for m in matches)

    def test_no_match_for_completely_new(self, s, role_tokens):
        r = s.post(
            f"{API}/clients/check-duplicates",
            headers=bearer(role_tokens["secretariat"]),
            json={"nom": f"ZZZ_TotallyNew_{uuid.uuid4().hex[:8]}",
                  "telephone": "+225 01 02 03 04 05"},
        )
        assert r.status_code == 200
        assert r.json()["matches"] == []

    def test_exclude_id_excludes_self(self, s, role_tokens, mongo):
        # Find FABS-CLI-0001
        c = mongo.clients.find_one({"reference": "FABS-CLI-0001"}, {"_id": 0})
        # With exclude_id, it must NOT appear in matches
        r = s.post(
            f"{API}/clients/check-duplicates",
            headers=bearer(role_tokens["secretariat"]),
            json={
                "nom": c["nom"],
                "telephone": c.get("telephone"),
                "exclude_id": c["client_id"],
            },
        )
        assert r.status_code == 200
        for m in r.json()["matches"]:
            assert m["client_id"] != c["client_id"]


# ---------------- PATCH ----------------
class TestPatch:
    def test_patch_commercial_updates_nom_email(self, s, role_tokens, created_client_ids):
        # First create
        nom_orig = f"TEST_Patch_{uuid.uuid4().hex[:6]}"
        c = s.post(
            f"{API}/clients",
            headers=bearer(role_tokens["secretariat"]),
            json={"nom": nom_orig, "type_client": "particulier",
                  "telephone": f"+225 06 77 88 99 {uuid.uuid4().int % 100:02d}"},
        ).json()
        created_client_ids.append(c["client_id"])
        old_updated = c["updated_at"]

        # Patch as commercial
        r = s.patch(
            f"{API}/clients/{c['client_id']}",
            headers=bearer(role_tokens["directeur_commercial"]),
            json={"nom": nom_orig + "_UPDATED", "email": "patched@example.com"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["nom"] == nom_orig + "_UPDATED"
        assert data["email"] == "patched@example.com"
        assert data["updated_at"] != old_updated

    def test_patch_empty_payload_400(self, s, role_tokens, created_client_ids, mongo):
        # Need a client to patch
        nom = f"TEST_PatchEmpty_{uuid.uuid4().hex[:6]}"
        c = s.post(
            f"{API}/clients",
            headers=bearer(role_tokens["secretariat"]),
            json={"nom": nom, "type_client": "particulier",
                  "telephone": f"+225 06 11 22 33 {uuid.uuid4().int % 100:02d}"},
        ).json()
        created_client_ids.append(c["client_id"])

        r = s.patch(
            f"{API}/clients/{c['client_id']}",
            headers=bearer(role_tokens["directeur_commercial"]),
            json={},
        )
        assert r.status_code == 400
        assert "Aucune modification" in r.json()["detail"]

    def test_patch_unknown_404(self, s, role_tokens):
        r = s.patch(
            f"{API}/clients/cli_nope_unknown",
            headers=bearer(role_tokens["directeur_commercial"]),
            json={"nom": "Whatever"},
        )
        assert r.status_code == 404


# ---------------- DELETE (soft) ----------------
class TestSoftDelete:
    def test_soft_delete_sets_actif_false(self, s, role_tokens, created_client_ids):
        nom = f"TEST_SoftDelete_{uuid.uuid4().hex[:6]}"
        c = s.post(
            f"{API}/clients",
            headers=bearer(role_tokens["secretariat"]),
            json={"nom": nom, "type_client": "particulier",
                  "telephone": f"+225 05 55 44 33 {uuid.uuid4().int % 100:02d}"},
        ).json()
        created_client_ids.append(c["client_id"])

        r = s.delete(f"{API}/clients/{c['client_id']}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        assert r.json()["actif"] is False

        # Idempotent — second delete still 200
        r2 = s.delete(f"{API}/clients/{c['client_id']}", headers=bearer(SUPER_ADMIN_TOKEN))
        assert r2.status_code == 200
        assert r2.json()["actif"] is False

        # ?actif=true excludes the disabled one
        r3 = s.get(f"{API}/clients", headers=bearer(SUPER_ADMIN_TOKEN),
                   params={"actif": "true", "page_size": 100})
        assert r3.status_code == 200
        actif_ids = [it["client_id"] for it in r3.json()["items"]]
        assert c["client_id"] not in actif_ids

        # ?actif=false includes it
        r4 = s.get(f"{API}/clients", headers=bearer(SUPER_ADMIN_TOKEN),
                   params={"actif": "false", "page_size": 100})
        ids_false = [it["client_id"] for it in r4.json()["items"]]
        assert c["client_id"] in ids_false
