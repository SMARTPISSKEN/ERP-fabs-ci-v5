"""
Comprehensive Backend API Testing for EDITIONS FABS-CI ERP
Tests all 12 modules as per review request
"""
import requests
import json
import sys
from typing import Optional, Dict, Any

# Backend URL - using localhost for testing (public URL not accessible from container)
BASE_URL = "http://localhost:8001/api"

# Test credentials from test_credentials.md
SUPER_ADMIN_EMAIL = "pissken@editionsfabsci.com"
SUPER_ADMIN_PASSWORD = "Admin@2025"
DG_EMAIL = "ali.mamin@editionsfabsci.com"
DG_PASSWORD = "DG@2025"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def print_header(text: str, level: int = 1):
    """Print formatted header"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}")
    elif level == 2:
        print(f"\n{'-'*80}")
        print(f"  {text}")
        print(f"{'-'*80}")
    else:
        print(f"\n  → {text}")

def print_result(success: bool, test_name: str, details: Optional[str] = None):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   Details: {details}")
    
    test_results["tests"].append({
        "name": test_name,
        "passed": success,
        "details": details
    })
    if success:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1

def test_endpoint(
    method: str,
    endpoint: str,
    test_name: str,
    token: Optional[str] = None,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expected_status: int = 200,
    check_fields: Optional[list] = None
) -> Optional[Dict[str, Any]]:
    """Generic endpoint tester"""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data, params=params, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=json_data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            print_result(False, test_name, f"Unsupported method: {method}")
            return None
        
        # Check status code
        if response.status_code != expected_status:
            print_result(False, test_name, 
                        f"Expected status {expected_status}, got {response.status_code}. Response: {response.text[:200]}")
            return None
        
        # Parse JSON
        try:
            data = response.json()
        except:
            if expected_status == 200:
                print_result(False, test_name, "Response is not valid JSON")
                return None
            data = {}
        
        # Check required fields
        if check_fields:
            missing = [f for f in check_fields if f not in data]
            if missing:
                print_result(False, test_name, f"Missing fields: {missing}")
                return None
        
        print_result(True, test_name, f"Status {response.status_code}")
        return data
        
    except requests.exceptions.Timeout:
        print_result(False, test_name, "Request timeout")
        return None
    except Exception as e:
        print_result(False, test_name, f"Exception: {str(e)}")
        return None

# ============================================================================
# MODULE 1: AUTHENTICATION
# ============================================================================
def test_authentication():
    """Test authentication module"""
    print_header("MODULE 1: AUTHENTICATION", 1)
    
    # Test 1: Health check
    print_header("Test: Health Check", 3)
    test_endpoint("GET", "/health", "GET /api/health", 
                 check_fields=["status"])
    
    # Test 2: Root endpoint
    print_header("Test: Root Endpoint", 3)
    test_endpoint("GET", "/", "GET /api/", 
                 check_fields=["status"])
    
    # Test 3: Login super admin
    print_header("Test: Login Super Admin", 3)
    login_data = test_endpoint("POST", "/auth/login", "POST /api/auth/login (super_admin)",
                              json_data={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
                              check_fields=["access_token", "token_type", "user"])
    
    if not login_data:
        print("\n❌ CRITICAL: Cannot login as super_admin. Stopping authentication tests.")
        return None, None
    
    super_admin_token = login_data["access_token"]
    
    # Test 4: Get profile
    print_header("Test: Get Profile", 3)
    test_endpoint("GET", "/auth/me", "GET /api/auth/me",
                 token=super_admin_token,
                 check_fields=["user_id", "email", "role", "nom_complet"])
    
    # Test 5: Login DG
    print_header("Test: Login DG", 3)
    dg_login_data = test_endpoint("POST", "/auth/login", "POST /api/auth/login (DG)",
                                 json_data={"email": DG_EMAIL, "password": DG_PASSWORD},
                                 check_fields=["access_token", "token_type", "user"])
    
    dg_token = dg_login_data["access_token"] if dg_login_data else None
    
    # Test 6: Logout
    print_header("Test: Logout", 3)
    test_endpoint("POST", "/auth/logout", "POST /api/auth/logout",
                 token=super_admin_token)
    
    return super_admin_token, dg_token

# ============================================================================
# MODULE 2: CLIENTS
# ============================================================================
def test_clients(token: str):
    """Test clients module"""
    print_header("MODULE 2: CLIENTS", 1)
    
    # Test 1: List clients
    print_header("Test: List Clients", 3)
    clients_data = test_endpoint("GET", "/clients", "GET /api/clients",
                                token=token,
                                check_fields=["items", "total", "page", "page_size"])
    
    if not clients_data or not clients_data.get("items"):
        print("⚠️  No clients found, skipping client detail tests")
        return None
    
    client_id = clients_data["items"][0]["client_id"]
    
    # Test 2: Get client detail
    print_header("Test: Get Client Detail", 3)
    test_endpoint("GET", f"/clients/{client_id}", f"GET /api/clients/{client_id}",
                 token=token,
                 check_fields=["client_id", "reference", "nom", "type_client"])
    
    # Test 3: Create client
    print_header("Test: Create Client", 3)
    new_client_data = {
        "nom": "Test Client ERP",
        "type_client": "librairie",
        "representant": "M. Test",
        "telephone": "+225 07 12 34 56 78",
        "email": "test@example.ci",
        "adresse": "Test Address",
        "ville": "Abidjan",
        "plafond_credit": 1000000,
        "notes": "Client de test"
    }
    created_client = test_endpoint("POST", "/clients", "POST /api/clients",
                                  token=token,
                                  json_data=new_client_data,
                                  params={"force": True},
                                  expected_status=201,
                                  check_fields=["client_id", "reference"])
    
    if created_client:
        new_client_id = created_client["client_id"]
        
        # Test 4: Update client
        print_header("Test: Update Client", 3)
        test_endpoint("PATCH", f"/clients/{new_client_id}", f"PATCH /api/clients/{new_client_id}",
                     token=token,
                     json_data={"notes": "Client modifié"},
                     check_fields=["client_id"])
        
        # Test 5: Soft delete client
        print_header("Test: Soft Delete Client", 3)
        test_endpoint("DELETE", f"/clients/{new_client_id}", f"DELETE /api/clients/{new_client_id}",
                     token=token,
                     check_fields=["client_id", "actif"])
    
    # Test 6: Check duplicates
    print_header("Test: Check Duplicates", 3)
    test_endpoint("POST", "/clients/check-duplicates", "POST /api/clients/check-duplicates",
                 token=token,
                 json_data={"nom": "Librairie de France", "telephone": "+225 27 22 44 30 30"},
                 check_fields=["matches"])
    
    return client_id

# ============================================================================
# MODULE 3: PRODUITS
# ============================================================================
def test_produits(token: str):
    """Test products module"""
    print_header("MODULE 3: PRODUITS", 1)
    
    # Test 1: List products
    print_header("Test: List Products", 3)
    products_data = test_endpoint("GET", "/produits", "GET /api/produits",
                                 token=token,
                                 check_fields=["items", "total", "page", "page_size"])
    
    if not products_data or not products_data.get("items"):
        print("⚠️  No products found, skipping product tests")
        return None
    
    product_id = products_data["items"][0]["product_id"]
    
    # Test 2: Get product detail
    print_header("Test: Get Product Detail", 3)
    test_endpoint("GET", f"/produits/{product_id}", f"GET /api/produits/{product_id}",
                 token=token,
                 check_fields=["product_id", "reference", "titre", "categorie"])
    
    # Test 3: Filter by category
    print_header("Test: Filter by Category", 3)
    test_endpoint("GET", "/produits", "GET /api/produits?categorie=primaire",
                 token=token,
                 params={"categorie": "primaire"},
                 check_fields=["items", "total"])
    
    # Test 4: Stock alerts
    print_header("Test: Stock Alerts", 3)
    test_endpoint("GET", "/produits/alertes-stock", "GET /api/produits/alertes-stock",
                 token=token,
                 check_fields=["items", "total"])
    
    # Test 5: Create product
    print_header("Test: Create Product", 3)
    new_product_data = {
        "titre": "Test Product ERP",
        "auteur": "Test Author",
        "collection": "Test Collection",
        "categorie": "primaire",
        "niveau_scolaire": "CP1",
        "isbn": "9782070999999",
        "prix_achat": 1000,
        "prix_vente": 2000,
        "stock_actuel": 50,
        "stock_minimum": 10
    }
    created_product = test_endpoint("POST", "/produits", "POST /api/produits",
                                   token=token,
                                   json_data=new_product_data,
                                   expected_status=201,
                                   check_fields=["product_id", "reference"])
    
    if created_product:
        new_product_id = created_product["product_id"]
        
        # Test 6: Update product
        print_header("Test: Update Product", 3)
        test_endpoint("PATCH", f"/produits/{new_product_id}", f"PATCH /api/produits/{new_product_id}",
                     token=token,
                     json_data={"stock_actuel": 100},
                     check_fields=["product_id"])
        
        # Test 7: Soft delete product
        print_header("Test: Soft Delete Product", 3)
        test_endpoint("DELETE", f"/produits/{new_product_id}", f"DELETE /api/produits/{new_product_id}",
                     token=token,
                     check_fields=["product_id", "actif"])
    
    return product_id

# ============================================================================
# MODULE 4: COMMANDES
# ============================================================================
def test_commandes(token: str, client_id: str, product_id: str):
    """Test orders module"""
    print_header("MODULE 4: COMMANDES", 1)
    
    # Test 1: List commandes
    print_header("Test: List Commandes", 3)
    commandes_data = test_endpoint("GET", "/commandes", "GET /api/commandes",
                                   token=token)
    
    # Check if response is array or paginated
    if isinstance(commandes_data, list):
        print("⚠️  WARNING: /api/commandes returns ARRAY instead of paginated object {items, total, page, page_size}")
        commandes_list = commandes_data
    elif isinstance(commandes_data, dict) and "items" in commandes_data:
        commandes_list = commandes_data["items"]
    else:
        print("❌ ERROR: Unexpected response format from /api/commandes")
        return None
    
    # Test 2: Create commande (brouillon)
    print_header("Test: Create Commande (Brouillon)", 3)
    new_commande_data = {
        "client_id": client_id,
        "date_livraison_prevue": "2026-06-01",
        "remise_globale": 0,
        "notes": "Commande de test",
        "lignes": [
            {
                "produit_id": product_id,
                "quantite": 10,
                "prix_unitaire": 2000,
                "remise_ligne": 0
            }
        ]
    }
    created_commande = test_endpoint("POST", "/commandes", "POST /api/commandes (brouillon)",
                                    token=token,
                                    json_data=new_commande_data,
                                    params={"submit": False},
                                    expected_status=201,
                                    check_fields=["commande_id", "reference", "statut"])
    
    if not created_commande:
        print("⚠️  Cannot create commande, skipping workflow tests")
        return None
    
    commande_id = created_commande["commande_id"]
    
    # Test 3: Get commande detail
    print_header("Test: Get Commande Detail", 3)
    test_endpoint("GET", f"/commandes/{commande_id}", f"GET /api/commandes/{commande_id}",
                 token=token,
                 check_fields=["commande_id", "reference", "lignes"])
    
    # Test 4: Update commande (brouillon only)
    print_header("Test: Update Commande", 3)
    test_endpoint("PATCH", f"/commandes/{commande_id}", f"PATCH /api/commandes/{commande_id}",
                 token=token,
                 json_data={"notes": "Commande modifiée"},
                 check_fields=["commande_id"])
    
    # Test 5: Create and submit commande
    print_header("Test: Create Commande (Submit)", 3)
    submitted_commande = test_endpoint("POST", "/commandes", "POST /api/commandes?submit=true",
                                      token=token,
                                      json_data=new_commande_data,
                                      params={"submit": True},
                                      expected_status=201,
                                      check_fields=["commande_id", "reference", "statut"])
    
    if submitted_commande:
        submitted_id = submitted_commande["commande_id"]
        
        # Test 6: Validate commande
        print_header("Test: Validate Commande", 3)
        validated = test_endpoint("POST", f"/commandes/{submitted_id}/valider", 
                                 f"POST /api/commandes/{submitted_id}/valider",
                                 token=token,
                                 check_fields=["commande_id", "statut"])
        
        if validated and validated.get("statut") == "validee":
            # Test 7: Prepare commande
            print_header("Test: Prepare Commande", 3)
            prepared = test_endpoint("POST", f"/commandes/{submitted_id}/preparer",
                                   f"POST /api/commandes/{submitted_id}/preparer",
                                   token=token,
                                   check_fields=["commande_id", "statut"])
            
            if prepared and prepared.get("statut") == "preparee":
                # Test 8: Deliver commande
                print_header("Test: Deliver Commande", 3)
                test_endpoint("POST", f"/commandes/{submitted_id}/livrer",
                            f"POST /api/commandes/{submitted_id}/livrer",
                            token=token,
                            check_fields=["commande_id", "statut"])
    
    # Test 9: Cancel commande
    print_header("Test: Cancel Commande", 3)
    test_endpoint("POST", f"/commandes/{commande_id}/annuler",
                 f"POST /api/commandes/{commande_id}/annuler",
                 token=token,
                 json_data={"motif": "Test d'annulation de commande pour validation du système"},
                 check_fields=["commande_id", "statut"])
    
    return submitted_id if submitted_commande else None

# ============================================================================
# MODULE 5: FACTURES
# ============================================================================
def test_factures(token: str, client_id: str, commande_id: Optional[str]):
    """Test invoices module"""
    print_header("MODULE 5: FACTURES", 1)
    
    # Test 1: List factures
    print_header("Test: List Factures", 3)
    factures_data = test_endpoint("GET", "/factures", "GET /api/factures",
                                 token=token)
    
    # Check response format
    if isinstance(factures_data, list):
        print("⚠️  WARNING: /api/factures returns ARRAY instead of paginated object")
        factures_list = factures_data
    elif isinstance(factures_data, dict) and "items" in factures_data:
        factures_list = factures_data["items"]
    else:
        factures_list = []
    
    # Test 2: Generate facture from commande
    if commande_id:
        print_header("Test: Generate Facture from Commande", 3)
        generated_facture = test_endpoint("POST", "/factures/generer-depuis-commande",
                                        "POST /api/factures/generer-depuis-commande",
                                        token=token,
                                        json_data={"commande_id": commande_id},
                                        expected_status=201,
                                        check_fields=["facture_id", "reference"])
        
        if generated_facture:
            facture_id = generated_facture["facture_id"]
            
            # Test 3: Get facture detail
            print_header("Test: Get Facture Detail", 3)
            test_endpoint("GET", f"/factures/{facture_id}", f"GET /api/factures/{facture_id}",
                         token=token,
                         check_fields=["facture_id", "reference", "montant_ht", "montant_tva", "montant_ttc"])
            
            # Test 4: Emit facture
            print_header("Test: Emit Facture", 3)
            test_endpoint("POST", f"/factures/{facture_id}/emettre",
                         f"POST /api/factures/{facture_id}/emettre",
                         token=token,
                         check_fields=["facture_id", "statut"])
            
            return facture_id
    
    # Test 5: Create manual facture
    print_header("Test: Create Manual Facture", 3)
    manual_facture_data = {
        "client_id": client_id,
        "date_facture": "2026-05-25",
        "date_echeance": "2026-06-25",
        "notes": "Facture manuelle de test",
        "lignes": [
            {
                "produit_id": "test_prod",
                "designation": "Test Product",
                "quantite": 5,
                "prix_unitaire": 1000,
                "remise_ligne": 0
            }
        ]
    }
    created_facture = test_endpoint("POST", "/factures", "POST /api/factures",
                                   token=token,
                                   json_data=manual_facture_data,
                                   expected_status=201,
                                   check_fields=["facture_id", "reference"])
    
    return created_facture["facture_id"] if created_facture else None

# ============================================================================
# MODULE 6: PAIEMENTS
# ============================================================================
def test_paiements(token: str, facture_id: Optional[str]):
    """Test payments module"""
    print_header("MODULE 6: PAIEMENTS", 1)
    
    # Test 1: List paiements
    print_header("Test: List Paiements", 3)
    test_endpoint("GET", "/paiements", "GET /api/paiements",
                 token=token)
    
    # Test 2: Create paiement
    if facture_id:
        print_header("Test: Create Paiement", 3)
        paiement_data = {
            "mode_paiement": "virement",
            "montant": 10000,
            "date_paiement": "2026-05-25",
            "reference_paiement": "TEST-PAY-001",
            "notes": "Paiement de test",
            "factures": [
                {
                    "facture_id": facture_id,
                    "montant_affecte": 10000
                }
            ]
        }
        created_paiement = test_endpoint("POST", "/paiements", "POST /api/paiements",
                                        token=token,
                                        json_data=paiement_data,
                                        expected_status=201,
                                        check_fields=["paiement_id", "reference"])
        
        if created_paiement:
            paiement_id = created_paiement["paiement_id"]
            
            # Test 3: Get paiement detail
            print_header("Test: Get Paiement Detail", 3)
            test_endpoint("GET", f"/paiements/{paiement_id}", f"GET /api/paiements/{paiement_id}",
                         token=token,
                         check_fields=["paiement_id", "reference"])
            
            # Test 4: Get paiements for facture
            print_header("Test: Get Paiements for Facture", 3)
            test_endpoint("GET", f"/paiements/facture/{facture_id}",
                         f"GET /api/paiements/facture/{facture_id}",
                         token=token)

# ============================================================================
# MODULE 7: ADMINISTRATION
# ============================================================================
def test_administration(super_admin_token: str, dg_token: Optional[str]):
    """Test administration module (users + parameters)"""
    print_header("MODULE 7: ADMINISTRATION", 1)
    
    # Test 1: List users (super_admin)
    print_header("Test: List Users (Super Admin)", 3)
    users_data = test_endpoint("GET", "/utilisateurs", "GET /api/utilisateurs (super_admin)",
                              token=super_admin_token)
    
    # Test 2: List users (DG - should fail)
    if dg_token:
        print_header("Test: List Users (DG - should fail 403)", 3)
        test_endpoint("GET", "/utilisateurs", "GET /api/utilisateurs (DG)",
                     token=dg_token,
                     expected_status=403)
    
    # Test 3: Get user detail
    if users_data and isinstance(users_data, list) and len(users_data) > 0:
        user_id = users_data[0]["user_id"]
        print_header("Test: Get User Detail", 3)
        test_endpoint("GET", f"/utilisateurs/{user_id}", f"GET /api/utilisateurs/{user_id}",
                     token=super_admin_token,
                     check_fields=["user_id", "email", "role"])
    
    # Test 4: List parameters
    print_header("Test: List Parameters", 3)
    params_data = test_endpoint("GET", "/parametres", "GET /api/parametres",
                               token=super_admin_token)
    
    # Test 5: Get parameter detail
    if params_data and isinstance(params_data, list) and len(params_data) > 0:
        param_cle = params_data[0]["cle"]
        print_header("Test: Get Parameter Detail", 3)
        test_endpoint("GET", f"/parametres/{param_cle}", f"GET /api/parametres/{param_cle}",
                     token=super_admin_token,
                     check_fields=["cle", "valeur"])
        
        # Test 6: Update parameter
        print_header("Test: Update Parameter", 3)
        test_endpoint("PATCH", f"/parametres/{param_cle}", f"PATCH /api/parametres/{param_cle}",
                     token=super_admin_token,
                     json_data={"valeur": "test_value"},
                     check_fields=["cle", "valeur"])

# ============================================================================
# MODULE 8-12: MEDIUM PRIORITY
# ============================================================================
def test_medium_priority_modules(token: str):
    """Test medium priority modules"""
    print_header("MEDIUM PRIORITY MODULES", 1)
    
    # Module 8: Stock
    print_header("Module 8: Stock", 2)
    test_endpoint("GET", "/stock/mouvements", "GET /api/stock/mouvements", token=token)
    
    # Module 9: Bons de Livraison
    print_header("Module 9: Bons de Livraison", 2)
    test_endpoint("GET", "/bons-livraison", "GET /api/bons-livraison", token=token)
    
    # Module 10: Bons de Retour
    print_header("Module 10: Bons de Retour", 2)
    test_endpoint("GET", "/bons-retour", "GET /api/bons-retour", token=token)
    
    # Module 11: Comptabilité
    print_header("Module 11: Comptabilité", 2)
    test_endpoint("GET", "/comptabilite/ecritures", "GET /api/comptabilite/ecritures", token=token)
    test_endpoint("GET", "/comptabilite/creances", "GET /api/comptabilite/creances", token=token)
    test_endpoint("GET", "/comptabilite/balance", "GET /api/comptabilite/balance", token=token)
    
    # Module 12: Dashboard
    print_header("Module 12: Dashboard", 2)
    test_endpoint("GET", "/dashboard/stats", "GET /api/dashboard/stats", token=token)
    
    # Module 13: Recherche Globale
    print_header("Module 13: Recherche Globale", 2)
    test_endpoint("GET", "/recherche/globale", "GET /api/recherche/globale?q=test",
                 token=token, params={"q": "test"})

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    """Run all backend tests"""
    print_header("ERP EDITIONS FABS-CI - COMPREHENSIVE BACKEND TESTING", 1)
    print(f"Backend URL: {BASE_URL}")
    print(f"Super Admin: {SUPER_ADMIN_EMAIL}")
    print(f"DG: {DG_EMAIL}")
    
    # Module 1: Authentication
    super_admin_token, dg_token = test_authentication()
    
    if not super_admin_token:
        print("\n❌ CRITICAL ERROR: Cannot authenticate. Stopping all tests.")
        return False
    
    # Module 2: Clients
    client_id = test_clients(super_admin_token)
    
    # Module 3: Produits
    product_id = test_produits(super_admin_token)
    
    # Module 4: Commandes
    commande_id = None
    if client_id and product_id:
        commande_id = test_commandes(super_admin_token, client_id, product_id)
    
    # Module 5: Factures
    facture_id = None
    if client_id:
        facture_id = test_factures(super_admin_token, client_id, commande_id)
    
    # Module 6: Paiements
    if facture_id:
        test_paiements(super_admin_token, facture_id)
    
    # Module 7: Administration
    test_administration(super_admin_token, dg_token)
    
    # Modules 8-13: Medium Priority
    test_medium_priority_modules(super_admin_token)
    
    # Print summary
    print_header("TEST SUMMARY", 1)
    print(f"Total Tests: {test_results['passed'] + test_results['failed']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    
    if test_results['failed'] > 0:
        print("\n❌ FAILED TESTS:")
        for test in test_results['tests']:
            if not test['passed']:
                print(f"  - {test['name']}")
                if test['details']:
                    print(f"    {test['details']}")
    
    success_rate = (test_results['passed'] / (test_results['passed'] + test_results['failed'])) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return test_results['failed'] == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
