"""
Comprehensive backend test for Essential Gemstones CMS multi-admin feature.
Tests all scenarios from A to H as specified in the review request.
"""
import requests
import json
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"

# Test credentials
MASTER_PASSWORD = "1121211221"
TEST_ADMIN_USERNAME = "luca"
TEST_ADMIN_PASSWORD = "lucapass"
TEST_ADMIN_NEW_PASSWORD = "newpass"

# Global variables to store tokens and IDs
master_token: Optional[str] = None
luca_token: Optional[str] = None
luca_id: Optional[str] = None

def print_test(name: str):
    """Print test name."""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print('='*80)

def print_result(passed: bool, message: str):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")

def print_response(response: requests.Response):
    """Print response details."""
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

# ============================================================================
# A) Legacy master password still works
# ============================================================================

def test_a1_master_password_login():
    """A1: POST /api/admin/login with master password returns token and user with isSuper=true"""
    global master_token
    print_test("A1: Master password login (no username)")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={"password": MASTER_PASSWORD}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check token exists
    if "token" not in data:
        print_result(False, "No token in response")
        return False
    
    master_token = data["token"]
    print(f"Master token: {master_token[:50]}...")
    
    # Check user object
    if "user" not in data:
        print_result(False, "No user object in response")
        return False
    
    user = data["user"]
    
    # Check isSuper
    if not user.get("isSuper"):
        print_result(False, f"isSuper is {user.get('isSuper')}, expected True")
        return False
    
    # Check permissions list exists and has all permissions
    if "permissions" not in user:
        print_result(False, "No permissions in user object")
        return False
    
    perms = user["permissions"]
    expected_section_perms = ["navbar", "hero", "products", "story", "promise", "chakra", "stats",
                               "lavaMeaning", "founder", "craft", "faq", "gallery", "vip", "footer"]
    expected_meta_perms = ["sectionOrder", "sectionVisibility", "manage_admins"]
    expected_all = expected_section_perms + expected_meta_perms
    
    if len(perms) != len(expected_all):
        print_result(False, f"Expected {len(expected_all)} permissions, got {len(perms)}")
        return False
    
    for perm in expected_all:
        if perm not in perms:
            print_result(False, f"Missing permission: {perm}")
            return False
    
    print_result(True, "Master password login works with correct user object (isSuper=true, full permissions)")
    return True

def test_a2_master_password_wrong():
    """A2: POST /api/admin/login with wrong password returns 401"""
    print_test("A2: Master password login with wrong password")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={"password": "wrong"}
    )
    print_response(response)
    
    if response.status_code != 401:
        print_result(False, f"Expected 401, got {response.status_code}")
        return False
    
    print_result(True, "Wrong password correctly returns 401")
    return True

# ============================================================================
# B) Permissions metadata endpoint
# ============================================================================

def test_b_permissions_endpoint():
    """B: GET /api/permissions returns sectionPermissions, metaPermissions, and all"""
    print_test("B: Permissions metadata endpoint")
    
    response = requests.get(f"{BASE_URL}/permissions")
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check sectionPermissions (14 keys)
    if "sectionPermissions" not in data:
        print_result(False, "No sectionPermissions in response")
        return False
    
    section_perms = data["sectionPermissions"]
    if len(section_perms) != 14:
        print_result(False, f"Expected 14 sectionPermissions, got {len(section_perms)}")
        return False
    
    # Check metaPermissions (3 keys)
    if "metaPermissions" not in data:
        print_result(False, "No metaPermissions in response")
        return False
    
    meta_perms = data["metaPermissions"]
    if len(meta_perms) != 3:
        print_result(False, f"Expected 3 metaPermissions, got {len(meta_perms)}")
        return False
    
    expected_meta = ["sectionOrder", "sectionVisibility", "manage_admins"]
    for perm in expected_meta:
        if perm not in meta_perms:
            print_result(False, f"Missing metaPermission: {perm}")
            return False
    
    # Check all array
    if "all" not in data:
        print_result(False, "No 'all' array in response")
        return False
    
    all_perms = data["all"]
    if len(all_perms) != 17:  # 14 + 3
        print_result(False, f"Expected 17 total permissions, got {len(all_perms)}")
        return False
    
    print_result(True, "Permissions endpoint returns correct structure (14 section, 3 meta, 17 total)")
    return True

# ============================================================================
# C) Admin user management (super only)
# ============================================================================

def test_c1_list_admins_empty():
    """C1: GET /api/admin/admins returns empty list initially"""
    print_test("C1: List admins (initially empty)")
    
    response = requests.get(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print_result(False, f"Expected list, got {type(data)}")
        return False
    
    print_result(True, f"List admins works, returned {len(data)} admins")
    return True

def test_c2_create_admin():
    """C2: POST /api/admin/admins creates new admin"""
    global luca_id
    print_test("C2: Create new admin 'luca'")
    
    response = requests.post(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"},
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": TEST_ADMIN_PASSWORD,
            "permissions": ["hero", "products"],
            "isSuper": False
        }
    )
    print_response(response)
    
    if response.status_code not in [200, 201]:
        print_result(False, f"Expected 200/201, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check required fields
    required_fields = ["id", "username", "permissions", "isSuper", "createdAt"]
    for field in required_fields:
        if field not in data:
            print_result(False, f"Missing field: {field}")
            return False
    
    # Check passwordHash is NOT returned
    if "passwordHash" in data:
        print_result(False, "passwordHash should NOT be returned")
        return False
    
    # Verify values
    if data["username"] != TEST_ADMIN_USERNAME:
        print_result(False, f"Expected username '{TEST_ADMIN_USERNAME}', got '{data['username']}'")
        return False
    
    if data["isSuper"] != False:
        print_result(False, f"Expected isSuper=False, got {data['isSuper']}")
        return False
    
    if set(data["permissions"]) != {"hero", "products"}:
        print_result(False, f"Expected permissions ['hero', 'products'], got {data['permissions']}")
        return False
    
    luca_id = data["id"]
    print(f"Created admin with ID: {luca_id}")
    
    print_result(True, "Admin created successfully with correct fields (no passwordHash)")
    return True

def test_c3_create_duplicate_admin():
    """C3: POST /api/admin/admins with duplicate username returns 400"""
    print_test("C3: Create duplicate admin")
    
    response = requests.post(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"},
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": "anotherpass",
            "permissions": ["hero"],
            "isSuper": False
        }
    )
    print_response(response)
    
    if response.status_code != 400:
        print_result(False, f"Expected 400, got {response.status_code}")
        return False
    
    print_result(True, "Duplicate username correctly returns 400")
    return True

def test_c4_create_reserved_username():
    """C4: POST /api/admin/admins with username 'master' returns 400"""
    print_test("C4: Create admin with reserved username 'master'")
    
    response = requests.post(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"},
        json={
            "username": "master",
            "password": "somepass",
            "permissions": ["hero"],
            "isSuper": False
        }
    )
    print_response(response)
    
    if response.status_code != 400:
        print_result(False, f"Expected 400, got {response.status_code}")
        return False
    
    print_result(True, "Reserved username 'master' correctly returns 400")
    return True

def test_c5_list_admins_with_luca():
    """C5: GET /api/admin/admins now contains 'luca'"""
    print_test("C5: List admins (should contain 'luca')")
    
    response = requests.get(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print_result(False, f"Expected list, got {type(data)}")
        return False
    
    if len(data) == 0:
        print_result(False, "Expected at least 1 admin, got 0")
        return False
    
    # Find luca
    luca_found = False
    for admin in data:
        if admin.get("username") == TEST_ADMIN_USERNAME:
            luca_found = True
            break
    
    if not luca_found:
        print_result(False, f"Admin '{TEST_ADMIN_USERNAME}' not found in list")
        return False
    
    print_result(True, f"List admins contains '{TEST_ADMIN_USERNAME}'")
    return True

# ============================================================================
# D) Login with new admin works
# ============================================================================

def test_d1_login_with_new_admin():
    """D1: POST /api/admin/login with luca credentials works"""
    global luca_token
    print_test("D1: Login with new admin 'luca'")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": TEST_ADMIN_PASSWORD
        }
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check token
    if "token" not in data:
        print_result(False, "No token in response")
        return False
    
    luca_token = data["token"]
    print(f"Luca token: {luca_token[:50]}...")
    
    # Check user object
    if "user" not in data:
        print_result(False, "No user object in response")
        return False
    
    user = data["user"]
    
    # Check isSuper=false
    if user.get("isSuper") != False:
        print_result(False, f"Expected isSuper=False, got {user.get('isSuper')}")
        return False
    
    # Check permissions
    if set(user.get("permissions", [])) != {"hero", "products"}:
        print_result(False, f"Expected permissions ['hero', 'products'], got {user.get('permissions')}")
        return False
    
    print_result(True, "Login with new admin works (isSuper=false, correct permissions)")
    return True

def test_d2_login_with_wrong_password():
    """D2: POST /api/admin/login with wrong password returns 401"""
    print_test("D2: Login with new admin 'luca' with wrong password")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": "WRONG"
        }
    )
    print_response(response)
    
    if response.status_code != 401:
        print_result(False, f"Expected 401, got {response.status_code}")
        return False
    
    print_result(True, "Wrong password correctly returns 401")
    return True

def test_d3_admin_me_with_luca_token():
    """D3: GET /api/admin/me with luca's token returns correct user"""
    print_test("D3: GET /api/admin/me with luca's token")
    
    response = requests.get(
        f"{BASE_URL}/admin/me",
        headers={"Authorization": f"Bearer {luca_token}"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    if "user" not in data:
        print_result(False, "No user object in response")
        return False
    
    user = data["user"]
    
    # Check isSuper=false
    if user.get("isSuper") != False:
        print_result(False, f"Expected isSuper=False, got {user.get('isSuper')}")
        return False
    
    # Check permissions
    if set(user.get("permissions", [])) != {"hero", "products"}:
        print_result(False, f"Expected permissions ['hero', 'products'], got {user.get('permissions')}")
        return False
    
    print_result(True, "GET /api/admin/me returns correct user (isSuper=false, correct permissions)")
    return True

# ============================================================================
# E) Permission enforcement on PUT /api/site
# ============================================================================

def test_e1_update_allowed_section():
    """E1: PUT /api/site with luca's token (hero permission) updates hero"""
    print_test("E1: Update allowed section (hero) with luca's token")
    
    # Update hero section
    response = requests.put(
        f"{BASE_URL}/site",
        headers={"Authorization": f"Bearer {luca_token}"},
        json={"hero": {"kicker": "Luca was here"}}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    # Verify update persisted
    response = requests.get(f"{BASE_URL}/site")
    data = response.json()
    
    if data.get("hero", {}).get("kicker") != "Luca was here":
        print_result(False, f"Hero kicker not updated. Got: {data.get('hero', {}).get('kicker')}")
        return False
    
    print_result(True, "Allowed section (hero) updated successfully")
    return True

def test_e2_update_forbidden_section():
    """E2: PUT /api/site with luca's token (no footer permission) rejects footer"""
    print_test("E2: Update forbidden section (footer) with luca's token")
    
    # Get current footer brand
    response = requests.get(f"{BASE_URL}/site")
    original_footer_brand = response.json().get("footer", {}).get("brand")
    print(f"Original footer brand: {original_footer_brand}")
    
    # Try to update footer section
    response = requests.put(
        f"{BASE_URL}/site",
        headers={"Authorization": f"Bearer {luca_token}"},
        json={"footer": {"brand": "X"}}
    )
    print_response(response)
    
    # Should either return 403 or return body with footer NOT updated and "_rejected" containing "footer"
    if response.status_code == 403:
        print_result(True, "Forbidden section correctly returns 403")
        return True
    
    if response.status_code == 200:
        data = response.json()
        
        # Check if footer is in _rejected
        if "_rejected" in data and "footer" in data["_rejected"]:
            # Verify footer.brand is unchanged
            response = requests.get(f"{BASE_URL}/site")
            current_footer_brand = response.json().get("footer", {}).get("brand")
            
            if current_footer_brand == original_footer_brand:
                print_result(True, "Forbidden section rejected, footer unchanged")
                return True
            else:
                print_result(False, f"Footer was updated despite rejection. Original: {original_footer_brand}, Current: {current_footer_brand}")
                return False
        else:
            print_result(False, "Expected '_rejected' to contain 'footer'")
            return False
    
    print_result(False, f"Unexpected status code: {response.status_code}")
    return False

def test_e3_update_mixed_sections():
    """E3: PUT /api/site with mixed allowed/forbidden sections"""
    print_test("E3: Update mixed sections (hero allowed, footer forbidden)")
    
    # Get current footer brand
    response = requests.get(f"{BASE_URL}/site")
    original_footer_brand = response.json().get("footer", {}).get("brand")
    
    # Try to update both hero and footer
    response = requests.put(
        f"{BASE_URL}/site",
        headers={"Authorization": f"Bearer {luca_token}"},
        json={
            "hero": {"kicker": "Mixed update test"},
            "footer": {"brand": "Should not update"}
        }
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check if footer is in _rejected
    if "_rejected" not in data or "footer" not in data["_rejected"]:
        print_result(False, "Expected '_rejected' to contain 'footer'")
        return False
    
    # Verify hero was updated
    response = requests.get(f"{BASE_URL}/site")
    site_data = response.json()
    
    if site_data.get("hero", {}).get("kicker") != "Mixed update test":
        print_result(False, f"Hero not updated. Got: {site_data.get('hero', {}).get('kicker')}")
        return False
    
    # Verify footer was NOT updated
    if site_data.get("footer", {}).get("brand") != original_footer_brand:
        print_result(False, f"Footer was updated despite rejection. Original: {original_footer_brand}, Current: {site_data.get('footer', {}).get('brand')}")
        return False
    
    print_result(True, "Mixed update: hero updated, footer rejected")
    return True

# ============================================================================
# F) Non-super cannot manage admins
# ============================================================================

def test_f1_non_super_list_admins():
    """F1: GET /api/admin/admins with luca's token returns 403"""
    print_test("F1: Non-super tries to list admins")
    
    response = requests.get(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {luca_token}"}
    )
    print_response(response)
    
    if response.status_code != 403:
        print_result(False, f"Expected 403, got {response.status_code}")
        return False
    
    print_result(True, "Non-super correctly cannot list admins (403)")
    return True

def test_f2_non_super_create_admin():
    """F2: POST /api/admin/admins with luca's token returns 403"""
    print_test("F2: Non-super tries to create admin")
    
    response = requests.post(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {luca_token}"},
        json={
            "username": "test",
            "password": "test",
            "permissions": ["hero"],
            "isSuper": False
        }
    )
    print_response(response)
    
    if response.status_code != 403:
        print_result(False, f"Expected 403, got {response.status_code}")
        return False
    
    print_result(True, "Non-super correctly cannot create admin (403)")
    return True

def test_f3_non_super_delete_admin():
    """F3: DELETE /api/admin/admins with luca's token returns 403"""
    print_test("F3: Non-super tries to delete admin")
    
    response = requests.delete(
        f"{BASE_URL}/admin/admins/some-id",
        headers={"Authorization": f"Bearer {luca_token}"}
    )
    print_response(response)
    
    if response.status_code != 403:
        print_result(False, f"Expected 403, got {response.status_code}")
        return False
    
    print_result(True, "Non-super correctly cannot delete admin (403)")
    return True

# ============================================================================
# G) Update admin endpoint
# ============================================================================

def test_g1_update_admin_permissions():
    """G1: PUT /api/admin/admins/{luca_id} updates permissions"""
    print_test("G1: Update admin permissions")
    
    response = requests.put(
        f"{BASE_URL}/admin/admins/{luca_id}",
        headers={"Authorization": f"Bearer {master_token}"},
        json={"permissions": ["hero", "products", "footer"]}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    if set(data.get("permissions", [])) != {"hero", "products", "footer"}:
        print_result(False, f"Expected permissions ['hero', 'products', 'footer'], got {data.get('permissions')}")
        return False
    
    print_result(True, "Admin permissions updated successfully")
    return True

def test_g2_update_admin_password():
    """G2: PUT /api/admin/admins/{luca_id} updates password"""
    print_test("G2: Update admin password")
    
    response = requests.put(
        f"{BASE_URL}/admin/admins/{luca_id}",
        headers={"Authorization": f"Bearer {master_token}"},
        json={"password": TEST_ADMIN_NEW_PASSWORD}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    print_result(True, "Admin password updated successfully")
    return True

def test_g3_login_with_new_password():
    """G3: Login with new password works"""
    global luca_token
    print_test("G3: Login with new password")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": TEST_ADMIN_NEW_PASSWORD
        }
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    if "token" not in data:
        print_result(False, "No token in response")
        return False
    
    luca_token = data["token"]
    
    print_result(True, "Login with new password works")
    return True

def test_g4_update_admin_to_super():
    """G4: PUT /api/admin/admins/{luca_id} with isSuper=true"""
    print_test("G4: Update admin to super admin")
    
    response = requests.put(
        f"{BASE_URL}/admin/admins/{luca_id}",
        headers={"Authorization": f"Bearer {master_token}"},
        json={"isSuper": True}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    if data.get("isSuper") != True:
        print_result(False, f"Expected isSuper=True, got {data.get('isSuper')}")
        return False
    
    # Check that permissions are now full
    if len(data.get("permissions", [])) != 17:  # All permissions
        print_result(False, f"Expected 17 permissions for super admin, got {len(data.get('permissions', []))}")
        return False
    
    print_result(True, "Admin updated to super admin with full permissions")
    return True

def test_g5_verify_admin_is_super():
    """G5: GET /api/admin/admins shows luca as super"""
    print_test("G5: Verify admin is super in list")
    
    response = requests.get(
        f"{BASE_URL}/admin/admins",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Find luca
    luca_admin = None
    for admin in data:
        if admin.get("id") == luca_id:
            luca_admin = admin
            break
    
    if not luca_admin:
        print_result(False, f"Admin with ID {luca_id} not found")
        return False
    
    if luca_admin.get("isSuper") != True:
        print_result(False, f"Expected isSuper=True, got {luca_admin.get('isSuper')}")
        return False
    
    print_result(True, "Admin list shows luca as super admin")
    return True

def test_g6_delete_admin():
    """G6: DELETE /api/admin/admins/{luca_id}"""
    print_test("G6: Delete admin")
    
    response = requests.delete(
        f"{BASE_URL}/admin/admins/{luca_id}",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    if data.get("ok") != True:
        print_result(False, f"Expected ok=True, got {data.get('ok')}")
        return False
    
    print_result(True, "Admin deleted successfully")
    return True

def test_g7_login_after_delete():
    """G7: Login with deleted admin returns 401"""
    print_test("G7: Login with deleted admin")
    
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={
            "username": TEST_ADMIN_USERNAME,
            "password": TEST_ADMIN_NEW_PASSWORD
        }
    )
    print_response(response)
    
    if response.status_code != 401:
        print_result(False, f"Expected 401, got {response.status_code}")
        return False
    
    print_result(True, "Login with deleted admin correctly returns 401")
    return True

# ============================================================================
# H) Upload still works
# ============================================================================

def test_h_upload_still_works():
    """H: POST /api/upload with master token works"""
    print_test("H: Upload still works")
    
    # Create a small PNG (1x1 transparent PNG)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])
    
    response = requests.post(
        f"{BASE_URL}/upload",
        headers={"Authorization": f"Bearer {master_token}"},
        files={"file": ("test.png", png_data, "image/png")}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check required fields
    required_fields = ["url", "kind", "size"]
    for field in required_fields:
        if field not in data:
            print_result(False, f"Missing field: {field}")
            return False
    
    if data["kind"] != "image":
        print_result(False, f"Expected kind='image', got '{data['kind']}'")
        return False
    
    print_result(True, "Upload still works correctly")
    return True

# ============================================================================
# Main test runner
# ============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*80)
    print("ESSENTIAL GEMSTONES CMS - MULTI-ADMIN FEATURE TEST SUITE")
    print("="*80)
    
    results = []
    
    # A) Legacy master password
    results.append(("A1: Master password login", test_a1_master_password_login()))
    results.append(("A2: Master password wrong", test_a2_master_password_wrong()))
    
    # B) Permissions endpoint
    results.append(("B: Permissions endpoint", test_b_permissions_endpoint()))
    
    # C) Admin user management
    results.append(("C1: List admins (empty)", test_c1_list_admins_empty()))
    results.append(("C2: Create admin", test_c2_create_admin()))
    results.append(("C3: Create duplicate admin", test_c3_create_duplicate_admin()))
    results.append(("C4: Create reserved username", test_c4_create_reserved_username()))
    results.append(("C5: List admins (with luca)", test_c5_list_admins_with_luca()))
    
    # D) Login with new admin
    results.append(("D1: Login with new admin", test_d1_login_with_new_admin()))
    results.append(("D2: Login with wrong password", test_d2_login_with_wrong_password()))
    results.append(("D3: Admin me with luca token", test_d3_admin_me_with_luca_token()))
    
    # E) Permission enforcement
    results.append(("E1: Update allowed section", test_e1_update_allowed_section()))
    results.append(("E2: Update forbidden section", test_e2_update_forbidden_section()))
    results.append(("E3: Update mixed sections", test_e3_update_mixed_sections()))
    
    # F) Non-super cannot manage admins
    results.append(("F1: Non-super list admins", test_f1_non_super_list_admins()))
    results.append(("F2: Non-super create admin", test_f2_non_super_create_admin()))
    results.append(("F3: Non-super delete admin", test_f3_non_super_delete_admin()))
    
    # G) Update admin endpoint
    results.append(("G1: Update admin permissions", test_g1_update_admin_permissions()))
    results.append(("G2: Update admin password", test_g2_update_admin_password()))
    results.append(("G3: Login with new password", test_g3_login_with_new_password()))
    results.append(("G4: Update admin to super", test_g4_update_admin_to_super()))
    results.append(("G5: Verify admin is super", test_g5_verify_admin_is_super()))
    results.append(("G6: Delete admin", test_g6_delete_admin()))
    results.append(("G7: Login after delete", test_g7_login_after_delete()))
    
    # H) Upload still works
    results.append(("H: Upload still works", test_h_upload_still_works()))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*80)
    
    return passed, failed

if __name__ == "__main__":
    passed, failed = run_all_tests()
    exit(0 if failed == 0 else 1)
