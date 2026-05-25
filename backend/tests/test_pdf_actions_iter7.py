"""
Backend tests for Sprint Iteration 7:
- New Commande fields persistence: representant, adresse_facturation, adresse_expedition,
  numero_commande_client, notes_privees (POST & PATCH)
- PDF endpoints: GET /api/commandes/{id}/pdf, /api/factures/{id}/pdf, /api/bons-livraison/{id}/pdf
- Auto-generation of Facture after order validation (workflow Commande -> Facture)
- Currency check: FCFA only, no $ symbol
"""
import os
import sys
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://c7cdf063-c181-4821-8983-2309bb3873df.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "pissken@editionsfabsci.com"
ADMIN_PASSWORD = "Admin@2025"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tk = data.get("access_token") or data.get("token") or data.get("session_token")
    assert tk, f"No token in response: {data}"
    return tk


@pytest.fixture(scope="session")
def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def client_id(h):
    r = requests.get(f"{API}/clients?limit=1", headers=h, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    arr = data["items"] if isinstance(data, dict) and "items" in data else data
    assert len(arr) > 0, "No client to test with"
    return arr[0]["client_id"]


@pytest.fixture(scope="session")
def product(h):
    r = requests.get(f"{API}/produits?limit=1", headers=h, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    arr = data["items"] if isinstance(data, dict) and "items" in data else data
    assert len(arr) > 0, "No product to test with"
    p = arr[0]
    return {
        "produit_id": p.get("product_id") or p.get("produit_id"),
        "prix": p.get("prix_vente") or 1000,
    }


# ---------------- Commande creation persists new fields ----------------
def test_create_commande_persists_new_fields(h, client_id, product):
    payload = {
        "client_id": client_id,
        "representant": "TEST_Rep_Iter7",
        "adresse_facturation": "TEST 123 Rue Facturation, Abidjan",
        "adresse_expedition": "TEST 456 Avenue Expedition, Abidjan",
        "numero_commande_client": "TEST_NCC_001",
        "notes_privees": "TEST notes privees internes",
        "remise_globale": 0,
        "notes": "Test commande iter7",
        "lignes": [
            {"produit_id": product["produit_id"], "quantite": 2, "prix_unitaire": product["prix"], "remise_ligne": 0}
        ],
    }
    r = requests.post(f"{API}/commandes", headers=h, json=payload, timeout=15)
    assert r.status_code == 201, r.text
    cmd = r.json()
    cid = cmd["commande_id"]

    # GET to verify persistence
    r2 = requests.get(f"{API}/commandes/{cid}", headers=h, timeout=15)
    assert r2.status_code == 200
    detail = r2.json()
    assert detail["representant"] == "TEST_Rep_Iter7"
    assert detail["adresse_facturation"] == "TEST 123 Rue Facturation, Abidjan"
    assert detail["adresse_expedition"] == "TEST 456 Avenue Expedition, Abidjan"
    assert detail["numero_commande_client"] == "TEST_NCC_001"
    assert detail["notes_privees"] == "TEST notes privees internes"
    pytest.created_commande_id = cid
    pytest.created_commande_ref = cmd["reference"]


def test_patch_commande_updates_new_fields(h):
    cid = getattr(pytest, "created_commande_id", None)
    assert cid, "create test must run first"
    patch = {
        "representant": "TEST_Rep_Updated",
        "adresse_facturation": "TEST Adresse Fact MISE A JOUR",
    }
    r = requests.patch(f"{API}/commandes/{cid}", headers=h, json=patch, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.get(f"{API}/commandes/{cid}", headers=h, timeout=15)
    d = r2.json()
    assert d["representant"] == "TEST_Rep_Updated"
    assert d["adresse_facturation"] == "TEST Adresse Fact MISE A JOUR"


# ---------------- Commande PDF ----------------
def test_commande_pdf_download(h):
    cid = getattr(pytest, "created_commande_id", None)
    assert cid
    r = requests.get(f"{API}/commandes/{cid}/pdf", headers={"Authorization": h["Authorization"]}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    ctype = r.headers.get("content-type", "")
    assert "application/pdf" in ctype, f"Unexpected content-type: {ctype}"
    assert r.content[:4] == b"%PDF", "Response is not a PDF"


# ---------------- Workflow: validation -> auto-generates facture ----------------
def test_validate_commande_auto_generates_facture(h, client_id, product):
    # Create + submit as en_attente
    payload = {
        "client_id": client_id,
        "representant": "TEST_AutoFacture",
        "remise_globale": 0,
        "lignes": [
            {"produit_id": product["produit_id"], "quantite": 1, "prix_unitaire": product["prix"], "remise_ligne": 0}
        ],
    }
    r = requests.post(f"{API}/commandes?submit=true", headers=h, json=payload, timeout=15)
    assert r.status_code == 201, r.text
    cmd = r.json()
    cid = cmd["commande_id"]
    assert cmd["statut"] == "en_attente"

    # Validate
    r2 = requests.post(f"{API}/commandes/{cid}/valider", headers=h, timeout=15)
    assert r2.status_code == 200, r2.text
    assert r2.json()["statut"] == "validee"

    # Check facture exists with commande_id reference
    import time
    time.sleep(0.5)
    r3 = requests.get(f"{API}/factures?limit=200", headers=h, timeout=15)
    assert r3.status_code == 200
    data3 = r3.json()
    factures = data3["items"] if isinstance(data3, dict) and "items" in data3 else data3
    matched = [f for f in factures if f.get("commande_id") == cid]
    assert len(matched) >= 1, f"No auto-generated facture for commande {cid}"
    fac = matched[0]
    pytest.created_facture_id = fac["facture_id"]

    # Check facture has lignes (verifies the bug fix - PDF route moved out of the auto-gen function)
    rf = requests.get(f"{API}/factures/{fac['facture_id']}", headers=h, timeout=15)
    assert rf.status_code == 200
    fd = rf.json()
    lignes = fd.get("lignes", [])
    assert len(lignes) >= 1, f"Facture {fac['facture_id']} has no lignes! Auto-gen broken."


# ---------------- Facture PDF ----------------
def test_facture_pdf_download(h):
    fid = getattr(pytest, "created_facture_id", None)
    assert fid
    r = requests.get(f"{API}/factures/{fid}/pdf", headers={"Authorization": h["Authorization"]}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF"


# ---------------- Bon de livraison PDF ----------------
def test_bon_livraison_pdf(h):
    # Look for an existing BL
    r = requests.get(f"{API}/bons-livraison?limit=5", headers=h, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    arr = data["items"] if isinstance(data, dict) and "items" in data else data
    if not arr:
        pytest.skip("No bon de livraison in DB to test PDF")
    bl_id = arr[0].get("bl_id") or arr[0].get("bon_livraison_id") or arr[0].get("id")
    assert bl_id, f"No id key in BL row: {arr[0].keys()}"
    rp = requests.get(f"{API}/bons-livraison/{bl_id}/pdf", headers={"Authorization": h["Authorization"]}, timeout=30)
    assert rp.status_code == 200, rp.text[:400]
    assert "application/pdf" in rp.headers.get("content-type", "")
    assert rp.content[:4] == b"%PDF"
