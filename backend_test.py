"""
Comprehensive backend test for Essential Gemstones Newsletter Subscription Feature
Tests all endpoints related to newsletter subscription functionality
"""
import requests
import json
from typing import Optional

# Backend URL from frontend/.env
BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"

# Test credentials
MASTER_PASSWORD = "1121211221"

# Test data
TEST_EMAIL_1 = "test+verify1@example.com"
TEST_EMAIL_2 = "test+verify2@example.com"
VIEWER_USERNAME = "viewer"
VIEWER_PASSWORD = "viewerpass"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log_test(name: str, passed: bool, details: str = ""):
    """Log test result with color coding"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")

def log_section(title: str):
    """Log section header"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def get_master_token() -> str:
    """Get master admin token"""
    response = requests.post(f"{BASE_URL}/admin/login", json={"password": MASTER_PASSWORD})
    if response.status_code == 200:
        return response.json()["token"]
    raise Exception(f"Failed to get master token: {response.status_code} {response.text}")

def get_viewer_token() -> str:
    """Get viewer admin token"""
    response = requests.post(f"{BASE_URL}/admin/login", json={"username": VIEWER_USERNAME, "password": VIEWER_PASSWORD})
    if response.status_code == 200:
        return response.json()["token"]
    raise Exception(f"Failed to get viewer token: {response.status_code} {response.text}")

# ============================================================================
# A) PUBLIC SUBSCRIBE ENDPOINT TESTS
# ============================================================================

def test_a_public_subscribe():
    log_section("A) PUBLIC SUBSCRIBE ENDPOINT TESTS")
    
    # A1: Valid email subscription
    response = requests.post(f"{BASE_URL}/subscribe", json={"email": TEST_EMAIL_1})
    passed = response.status_code == 200
    if passed:
        data = response.json()
        passed = (
            data.get("ok") is True and
            data.get("alreadySubscribed") is False and
            "notifySent" in data and
            "welcomeSent" in data and
            "error" in data
        )
        details = f"Response: {json.dumps(data, indent=2)}"
        if data.get("error"):
            details += f"\n       {YELLOW}Note: Email error (expected if SMTP fails): {data['error']}{RESET}"
    else:
        details = f"Status: {response.status_code}, Body: {response.text}"
    log_test("A1: POST /api/subscribe with valid email", passed, details)
    
    # A2: Duplicate email subscription
    response = requests.post(f"{BASE_URL}/subscribe", json={"email": TEST_EMAIL_1})
    passed = response.status_code == 200
    if passed:
        data = response.json()
        passed = data.get("alreadySubscribed") is True
        details = f"alreadySubscribed: {data.get('alreadySubscribed')}"
    else:
        details = f"Status: {response.status_code}, Body: {response.text}"
    log_test("A2: POST /api/subscribe with duplicate email", passed, details)
    
    # A3: Invalid email format
    response = requests.post(f"{BASE_URL}/subscribe", json={"email": "not-an-email"})
    passed = response.status_code == 422
    details = f"Status: {response.status_code}"
    log_test("A3: POST /api/subscribe with invalid email format", passed, details)
    
    # A4: Missing email field
    response = requests.post(f"{BASE_URL}/subscribe", json={})
    passed = response.status_code == 422
    details = f"Status: {response.status_code}"
    log_test("A4: POST /api/subscribe with missing email", passed, details)

# ============================================================================
# B) SUBSCRIBER STORAGE VERIFICATION
# ============================================================================

def test_b_subscriber_storage():
    log_section("B) SUBSCRIBER STORAGE VERIFICATION")
    
    # B1: Get master token and list subscribers
    try:
        token = get_master_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
        passed = response.status_code == 200
        if passed:
            data = response.json()
            passed = isinstance(data, list)
            if passed:
                # Check if TEST_EMAIL_1 is in the list
                found = any(sub.get("email") == TEST_EMAIL_1 for sub in data)
                passed = found
                if found:
                    subscriber = next(sub for sub in data if sub.get("email") == TEST_EMAIL_1)
                    has_fields = all(k in subscriber for k in ["id", "email", "createdAt"])
                    passed = has_fields
                    details = f"Found subscriber: {json.dumps(subscriber, indent=2)}"
                else:
                    details = f"Subscriber {TEST_EMAIL_1} not found in list of {len(data)} subscribers"
            else:
                details = f"Response is not a list: {data}"
        else:
            details = f"Status: {response.status_code}, Body: {response.text}"
        log_test("B1: GET /api/admin/subscribers returns subscriber list with correct fields", passed, details)
    except Exception as e:
        log_test("B1: GET /api/admin/subscribers returns subscriber list with correct fields", False, str(e))

# ============================================================================
# C) SUBSCRIBER PERMISSIONS ENFORCEMENT
# ============================================================================

def test_c_permissions_enforcement():
    log_section("C) SUBSCRIBER PERMISSIONS ENFORCEMENT")
    
    # C1: Access without token
    response = requests.get(f"{BASE_URL}/admin/subscribers")
    passed = response.status_code == 401
    details = f"Status: {response.status_code}"
    log_test("C1: GET /api/admin/subscribers without token returns 401", passed, details)
    
    # C2: Create non-super admin with no permissions
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # First, delete viewer if exists
        response = requests.get(f"{BASE_URL}/admin/admins", headers=headers)
        if response.status_code == 200:
            admins = response.json()
            for admin in admins:
                if admin.get("username") == VIEWER_USERNAME:
                    requests.delete(f"{BASE_URL}/admin/admins/{admin['id']}", headers=headers)
        
        # Create viewer with no permissions
        response = requests.post(
            f"{BASE_URL}/admin/admins",
            headers=headers,
            json={
                "username": VIEWER_USERNAME,
                "password": VIEWER_PASSWORD,
                "permissions": [],
                "isSuper": False
            }
        )
        passed = response.status_code == 200
        if passed:
            data = response.json()
            passed = (
                data.get("username") == VIEWER_USERNAME and
                data.get("isSuper") is False and
                data.get("permissions") == []
            )
            details = f"Created admin: {json.dumps(data, indent=2)}"
        else:
            details = f"Status: {response.status_code}, Body: {response.text}"
        log_test("C2: Create non-super admin with no permissions", passed, details)
    except Exception as e:
        log_test("C2: Create non-super admin with no permissions", False, str(e))
    
    # C3: Login as viewer and try to access subscribers (should fail)
    try:
        viewer_token = get_viewer_token()
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
        passed = response.status_code == 403
        details = f"Status: {response.status_code}"
        log_test("C3: GET /api/admin/subscribers with viewer (no permissions) returns 403", passed, details)
    except Exception as e:
        log_test("C3: GET /api/admin/subscribers with viewer (no permissions) returns 403", False, str(e))
    
    # C4: Update viewer's permissions to include manage_subscribers
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # Get viewer's ID
        response = requests.get(f"{BASE_URL}/admin/admins", headers=headers)
        admins = response.json()
        viewer = next((a for a in admins if a.get("username") == VIEWER_USERNAME), None)
        
        if viewer:
            viewer_id = viewer["id"]
            response = requests.put(
                f"{BASE_URL}/admin/admins/{viewer_id}",
                headers=headers,
                json={"permissions": ["manage_subscribers"]}
            )
            passed = response.status_code == 200
            if passed:
                data = response.json()
                passed = "manage_subscribers" in data.get("permissions", [])
                details = f"Updated permissions: {data.get('permissions')}"
            else:
                details = f"Status: {response.status_code}, Body: {response.text}"
        else:
            passed = False
            details = "Viewer admin not found"
        log_test("C4: Update viewer's permissions to include manage_subscribers", passed, details)
    except Exception as e:
        log_test("C4: Update viewer's permissions to include manage_subscribers", False, str(e))
    
    # C5: Login as viewer again and access subscribers (should succeed)
    try:
        viewer_token = get_viewer_token()
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
        passed = response.status_code == 200
        if passed:
            data = response.json()
            passed = isinstance(data, list)
            details = f"Successfully retrieved {len(data)} subscribers"
        else:
            details = f"Status: {response.status_code}, Body: {response.text}"
        log_test("C5: GET /api/admin/subscribers with viewer (manage_subscribers permission) returns 200", passed, details)
    except Exception as e:
        log_test("C5: GET /api/admin/subscribers with viewer (manage_subscribers permission) returns 200", False, str(e))

# ============================================================================
# D) DELETE SUBSCRIBER TESTS
# ============================================================================

def test_d_delete_subscriber():
    log_section("D) DELETE SUBSCRIBER TESTS")
    
    # D1: Get subscriber ID and delete
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        
        # Get subscribers list
        response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
        subscribers = response.json()
        subscriber = next((s for s in subscribers if s.get("email") == TEST_EMAIL_1), None)
        
        if subscriber:
            subscriber_id = subscriber["id"]
            response = requests.delete(f"{BASE_URL}/admin/subscribers/{subscriber_id}", headers=headers)
            passed = response.status_code == 200
            if passed:
                data = response.json()
                passed = data.get("ok") is True
                details = f"Response: {json.dumps(data)}"
            else:
                details = f"Status: {response.status_code}, Body: {response.text}"
        else:
            passed = False
            details = f"Subscriber {TEST_EMAIL_1} not found"
        log_test("D1: DELETE /api/admin/subscribers/{id} with master token returns 200", passed, details)
    except Exception as e:
        log_test("D1: DELETE /api/admin/subscribers/{id} with master token returns 200", False, str(e))
    
    # D2: Verify subscriber is deleted
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
        subscribers = response.json()
        found = any(s.get("email") == TEST_EMAIL_1 for s in subscribers)
        passed = not found
        details = f"Subscriber {TEST_EMAIL_1} {'still exists' if found else 'successfully deleted'}"
        log_test("D2: GET /api/admin/subscribers confirms deletion", passed, details)
    except Exception as e:
        log_test("D2: GET /api/admin/subscribers confirms deletion", False, str(e))
    
    # D3: Delete non-existent subscriber
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.delete(f"{BASE_URL}/admin/subscribers/nonexistent-id", headers=headers)
        passed = response.status_code == 404
        details = f"Status: {response.status_code}"
        log_test("D3: DELETE /api/admin/subscribers/nonexistent-id returns 404", passed, details)
    except Exception as e:
        log_test("D3: DELETE /api/admin/subscribers/nonexistent-id returns 404", False, str(e))

# ============================================================================
# E) TEST EMAIL ENDPOINT
# ============================================================================

def test_e_test_email():
    log_section("E) TEST EMAIL ENDPOINT")
    
    # E1: Test email with master token
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(
            f"{BASE_URL}/admin/test-email",
            headers=headers,
            json={"to": "test@example.com"}
        )
        passed = response.status_code in [200, 500]  # Either works or SMTP fails
        if response.status_code == 200:
            details = f"{GREEN}SMTP working! Email sent successfully{RESET}"
        else:
            details = f"{YELLOW}SMTP failed (expected): {response.json().get('detail')}{RESET}"
        log_test("E1: POST /api/admin/test-email with master token", passed, details)
    except Exception as e:
        log_test("E1: POST /api/admin/test-email with master token", False, str(e))
    
    # E2: Test email without token
    response = requests.post(f"{BASE_URL}/admin/test-email", json={"to": "test@example.com"})
    passed = response.status_code == 401
    details = f"Status: {response.status_code}"
    log_test("E2: POST /api/admin/test-email without token returns 401", passed, details)
    
    # E3: Test email with viewer token (should fail - super only)
    try:
        viewer_token = get_viewer_token()
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = requests.post(
            f"{BASE_URL}/admin/test-email",
            headers=headers,
            json={"to": "test@example.com"}
        )
        passed = response.status_code == 403
        details = f"Status: {response.status_code}"
        log_test("E3: POST /api/admin/test-email with viewer token returns 403", passed, details)
    except Exception as e:
        log_test("E3: POST /api/admin/test-email with viewer token returns 403", False, str(e))
    
    # E4: Test email with missing 'to' field
    try:
        master_token = get_master_token()
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(f"{BASE_URL}/admin/test-email", headers=headers, json={})
        passed = response.status_code == 400
        details = f"Status: {response.status_code}"
        log_test("E4: POST /api/admin/test-email with missing 'to' returns 400", passed, details)
    except Exception as e:
        log_test("E4: POST /api/admin/test-email with missing 'to' returns 400", False, str(e))

# ============================================================================
# F) PERMISSIONS METADATA UPDATED
# ============================================================================

def test_f_permissions_metadata():
    log_section("F) PERMISSIONS METADATA UPDATED")
    
    response = requests.get(f"{BASE_URL}/permissions")
    passed = response.status_code == 200
    if passed:
        data = response.json()
        meta_perms = data.get("metaPermissions", [])
        all_perms = data.get("all", [])
        
        has_manage_subscribers = "manage_subscribers" in meta_perms
        correct_meta_count = len(meta_perms) == 4  # sectionOrder, sectionVisibility, manage_admins, manage_subscribers
        correct_all_count = len(all_perms) == 18  # 14 sections + 4 meta
        
        passed = has_manage_subscribers and correct_meta_count and correct_all_count
        details = f"metaPermissions: {meta_perms}\n"
        details += f"       metaPermissions count: {len(meta_perms)} (expected 4)\n"
        details += f"       all permissions count: {len(all_perms)} (expected 18)\n"
        details += f"       manage_subscribers present: {has_manage_subscribers}"
    else:
        details = f"Status: {response.status_code}, Body: {response.text}"
    log_test("F1: GET /api/permissions includes manage_subscribers in metaPermissions", passed, details)

# ============================================================================
# G) SUBSCRIBE SAVES EVEN IF SMTP FAILS
# ============================================================================

def test_g_subscribe_saves_on_smtp_fail():
    log_section("G) SUBSCRIBE SAVES EVEN IF SMTP FAILS")
    
    # G1: Subscribe with a new email
    response = requests.post(f"{BASE_URL}/subscribe", json={"email": TEST_EMAIL_2})
    passed = response.status_code == 200
    if passed:
        data = response.json()
        passed = data.get("ok") is True
        details = f"Response: {json.dumps(data, indent=2)}\n"
        
        # Check if subscriber was saved even if SMTP failed
        if data.get("error"):
            details += f"       {YELLOW}SMTP failed (as expected), but checking if subscriber was saved...{RESET}"
        
        # Verify subscriber was saved
        try:
            master_token = get_master_token()
            headers = {"Authorization": f"Bearer {master_token}"}
            response = requests.get(f"{BASE_URL}/admin/subscribers", headers=headers)
            subscribers = response.json()
            found = any(s.get("email") == TEST_EMAIL_2 for s in subscribers)
            passed = found
            details += f"\n       Subscriber saved to database: {found}"
        except Exception as e:
            passed = False
            details += f"\n       Error checking database: {str(e)}"
    else:
        details = f"Status: {response.status_code}, Body: {response.text}"
    log_test("G1: POST /api/subscribe saves subscriber even if SMTP fails", passed, details)

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}ESSENTIAL GEMSTONES - NEWSLETTER SUBSCRIPTION FEATURE TEST SUITE{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    print(f"Backend URL: {BASE_URL}\n")
    
    try:
        test_a_public_subscribe()
        test_b_subscriber_storage()
        test_c_permissions_enforcement()
        test_d_delete_subscriber()
        test_e_test_email()
        test_f_permissions_metadata()
        test_g_subscribe_saves_on_smtp_fail()
        
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}TEST SUITE COMPLETE{RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")
        
    except Exception as e:
        print(f"\n{RED}FATAL ERROR: {str(e)}{RESET}\n")
        raise

if __name__ == "__main__":
    main()
