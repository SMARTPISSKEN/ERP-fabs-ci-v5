"""
Backend API Testing for EDITIONS FABS-CI ERP
Tests authentication endpoints as requested
"""
import requests
import json

# Backend URL as specified in the review request
BASE_URL = "http://localhost:8001"

# Test credentials from test_credentials.md
TEST_EMAIL = "pissken@editionsfabsci.com"
TEST_PASSWORD = "Admin@2025"

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")

def print_result(success, message, details=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    if details:
        print(f"Details: {json.dumps(details, indent=2)}")

def test_health_check():
    """Test 1: Health check endpoint"""
    print_test_header("Health Check - GET /api/health")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Verify status code
        if response.status_code != 200:
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False
        
        # Verify response structure
        data = response.json()
        if "status" not in data or data["status"] != "ok":
            print_result(False, "Response missing 'status': 'ok'", data)
            return False
        
        print_result(True, "Health check endpoint working correctly", data)
        return True
        
    except Exception as e:
        print_result(False, f"Health check failed with exception: {str(e)}")
        return False

def test_login():
    """Test 2: Login with valid credentials"""
    print_test_header("Login - POST /api/auth/login")
    
    try:
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=payload,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Verify status code
        if response.status_code != 200:
            print(f"Response: {response.text}")
            print_result(False, f"Expected status 200, got {response.status_code}")
            return None
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        required_fields = ["access_token", "token_type", "user"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return None
        
        # Verify user role
        if "user" not in data or "role" not in data["user"]:
            print_result(False, "User object missing or no role field", data)
            return None
        
        if data["user"]["role"] != "super_admin":
            print_result(False, f"Expected role 'super_admin', got '{data['user']['role']}'", data)
            return None
        
        print_result(True, "Login successful with correct response structure", {
            "token_type": data["token_type"],
            "user_role": data["user"]["role"],
            "user_email": data["user"]["email"]
        })
        
        return data["access_token"]
        
    except Exception as e:
        print_result(False, f"Login failed with exception: {str(e)}")
        return None

def test_get_profile(token):
    """Test 3: Get profile with token"""
    print_test_header("Get Profile - GET /api/auth/me")
    
    if not token:
        print_result(False, "No token available from login test")
        return False
    
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print(f"Request headers: Authorization: Bearer {token[:20]}...")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=headers,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Verify status code
        if response.status_code != 200:
            print(f"Response: {response.text}")
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify response contains user details
        required_fields = ["user_id", "email", "nom_complet", "role", "actif"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        # Verify email matches
        if data["email"] != TEST_EMAIL:
            print_result(False, f"Email mismatch: expected {TEST_EMAIL}, got {data['email']}", data)
            return False
        
        print_result(True, "Profile retrieval successful with correct user details", {
            "user_id": data["user_id"],
            "email": data["email"],
            "role": data["role"],
            "nom_complet": data["nom_complet"]
        })
        
        return True
        
    except Exception as e:
        print_result(False, f"Get profile failed with exception: {str(e)}")
        return False

def test_clients_api_structure(token):
    """Test 4: Verify GET /api/clients returns paginated structure"""
    print_test_header("Clients API Structure - GET /api/clients?limit=5")
    
    if not token:
        print_result(False, "No token available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/clients?limit=5",
            headers=headers,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Response: {response.text}")
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        print(f"Response structure: {json.dumps({k: type(v).__name__ for k, v in data.items()}, indent=2)}")
        print(f"Full response: {json.dumps(data, indent=2)}")
        
        # Verify paginated structure
        required_fields = ["items", "total", "page", "page_size"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        # Verify items is an array
        if not isinstance(data["items"], list):
            print_result(False, f"'items' should be an array, got {type(data['items']).__name__}", data)
            return False
        
        # Verify numeric fields
        if not isinstance(data["total"], int):
            print_result(False, f"'total' should be a number, got {type(data['total']).__name__}", data)
            return False
        
        if not isinstance(data["page"], int):
            print_result(False, f"'page' should be a number, got {type(data['page']).__name__}", data)
            return False
        
        if not isinstance(data["page_size"], int):
            print_result(False, f"'page_size' should be a number, got {type(data['page_size']).__name__}", data)
            return False
        
        print_result(True, "Clients API returns correct paginated structure", {
            "structure": "✅ {items: array, total: number, page: number, page_size: number}",
            "items_count": len(data["items"]),
            "total": data["total"],
            "page": data["page"],
            "page_size": data["page_size"]
        })
        
        return True
        
    except Exception as e:
        print_result(False, f"Test failed with exception: {str(e)}")
        return False

def test_produits_api_structure(token):
    """Test 5: Verify GET /api/produits returns paginated structure"""
    print_test_header("Produits API Structure - GET /api/produits?limit=5")
    
    if not token:
        print_result(False, "No token available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/produits?limit=5",
            headers=headers,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Response: {response.text}")
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        print(f"Response structure: {json.dumps({k: type(v).__name__ for k, v in data.items()}, indent=2)}")
        print(f"Full response: {json.dumps(data, indent=2)}")
        
        # Verify paginated structure
        required_fields = ["items", "total", "page", "page_size"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        # Verify items is an array
        if not isinstance(data["items"], list):
            print_result(False, f"'items' should be an array, got {type(data['items']).__name__}", data)
            return False
        
        # Verify numeric fields
        if not isinstance(data["total"], int):
            print_result(False, f"'total' should be a number, got {type(data['total']).__name__}", data)
            return False
        
        if not isinstance(data["page"], int):
            print_result(False, f"'page' should be a number, got {type(data['page']).__name__}", data)
            return False
        
        if not isinstance(data["page_size"], int):
            print_result(False, f"'page_size' should be a number, got {type(data['page_size']).__name__}", data)
            return False
        
        print_result(True, "Produits API returns correct paginated structure", {
            "structure": "✅ {items: array, total: number, page: number, page_size: number}",
            "items_count": len(data["items"]),
            "total": data["total"],
            "page": data["page"],
            "page_size": data["page_size"]
        })
        
        return True
        
    except Exception as e:
        print_result(False, f"Test failed with exception: {str(e)}")
        return False

def test_commandes_api_structure(token):
    """Test 6: Verify GET /api/commandes returns paginated structure"""
    print_test_header("Commandes API Structure - GET /api/commandes?limit=5")
    
    if not token:
        print_result(False, "No token available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/commandes?limit=5",
            headers=headers,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Response: {response.text}")
            print_result(False, f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check if it's a direct array (current implementation)
        if isinstance(data, list):
            print(f"⚠️  WARNING: API returns a DIRECT ARRAY, not a paginated object!")
            print(f"Current response type: {type(data).__name__}")
            print(f"Array length: {len(data)}")
            print(f"Sample response: {json.dumps(data[:2] if len(data) > 0 else [], indent=2)}")
            print_result(False, "❌ API returns array instead of paginated object {items, total, page, page_size}", {
                "expected": "{items: array, total: number, page: number, page_size: number}",
                "actual": "array (direct)",
                "array_length": len(data)
            })
            return False
        
        # Check for paginated structure
        print(f"Response structure: {json.dumps({k: type(v).__name__ for k, v in data.items()}, indent=2)}")
        print(f"Full response: {json.dumps(data, indent=2)}")
        
        # Verify paginated structure
        required_fields = ["items", "total", "page", "page_size"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        # Verify items is an array
        if not isinstance(data["items"], list):
            print_result(False, f"'items' should be an array, got {type(data['items']).__name__}", data)
            return False
        
        # Verify numeric fields
        if not isinstance(data["total"], int):
            print_result(False, f"'total' should be a number, got {type(data['total']).__name__}", data)
            return False
        
        if not isinstance(data["page"], int):
            print_result(False, f"'page' should be a number, got {type(data['page']).__name__}", data)
            return False
        
        if not isinstance(data["page_size"], int):
            print_result(False, f"'page_size' should be a number, got {type(data['page_size']).__name__}", data)
            return False
        
        print_result(True, "Commandes API returns correct paginated structure", {
            "structure": "✅ {items: array, total: number, page: number, page_size: number}",
            "items_count": len(data["items"]),
            "total": data["total"],
            "page": data["page"],
            "page_size": data["page_size"]
        })
        
        return True
        
    except Exception as e:
        print_result(False, f"Test failed with exception: {str(e)}")
        return False

def run_all_tests():
    """Run all authentication tests"""
    print("\n" + "="*60)
    print("BACKEND API STRUCTURE TESTING")
    print("="*60)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")
    print("="*60)
    
    results = {
        "health_check": False,
        "login": False,
        "get_profile": False,
        "clients_api_structure": False,
        "produits_api_structure": False,
        "commandes_api_structure": False
    }
    
    # Test 1: Health check
    results["health_check"] = test_health_check()
    
    # Test 2: Login
    token = test_login()
    results["login"] = token is not None
    
    # Test 3: Get profile (only if login succeeded)
    if token:
        results["get_profile"] = test_get_profile(token)
        
        # Test 4-6: API structure tests
        results["clients_api_structure"] = test_clients_api_structure(token)
        results["produits_api_structure"] = test_produits_api_structure(token)
        results["commandes_api_structure"] = test_commandes_api_structure(token)
    else:
        print_test_header("API Structure Tests - SKIPPED (no token)")
        print("⚠️  Skipped: Login test failed, no token available")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    print("="*60)
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
