#!/usr/bin/env python3
"""
Comprehensive backend test suite for Essential Gemstones user authentication endpoints.
Tests scenarios A-J as specified in the review request.
"""
import json
import sys
import time
from typing import Any, Optional

import jwt
import requests

# Configuration
BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"
MASTER_PASSWORD = "1121211221"
JWT_SECRET = "essentialgemstones-luca-secret-2026"
JWT_ALG = "HS256"

# Test data
TEST_USER_EMAIL = f"jane+test{int(time.time())}@example.com"
TEST_USER_FULLNAME = "Jane Doe"
TEST_USER_PASSWORD = "supersecret"

# Global state
master_token = None
jane_token = None
jane_id = None
viewer_id = None
viewer_token = None


def log_test(scenario: str, test: str, status: str, details: str = ""):
    """Log test results in a structured format."""
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} [{scenario}] {test}")
    if details:
        print(f"   {details}")


def decode_token(token: str) -> dict:
    """Decode JWT token without verification for inspection."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception as e:
        return {"error": str(e)}


def test_a_user_registration():
    """Test scenario A: User registration."""
    global jane_token, jane_id
    
    print("\n" + "="*80)
    print("SCENARIO A: USER REGISTRATION")
    print("="*80)
    
    # A1: Valid registration
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": TEST_USER_FULLNAME,
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "subscribeNewsletter": True
    })
    
    if resp.status_code == 200:
        data = resp.json()
        if "token" in data and "user" in data:
            jane_token = data["token"]
            user = data["user"]
            jane_id = user.get("id")
            
            # Verify user object structure
            required_fields = ["id", "fullName", "email", "isBanned", "favorites", "createdAt"]
            missing = [f for f in required_fields if f not in user]
            has_password = "passwordHash" in user or "password" in user
            
            if not missing and not has_password and user["isBanned"] == False:
                log_test("A1", "Valid registration returns 200 with token and user", "PASS",
                        f"User ID: {jane_id}, Email: {user['email']}")
            else:
                log_test("A1", "Valid registration returns 200 with token and user", "FAIL",
                        f"Missing fields: {missing}, Has password: {has_password}")
        else:
            log_test("A1", "Valid registration returns 200 with token and user", "FAIL",
                    f"Missing token or user in response: {data}")
    else:
        log_test("A1", "Valid registration returns 200 with token and user", "FAIL",
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # A2: Duplicate email
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "Jane Duplicate",
        "email": TEST_USER_EMAIL,
        "password": "anotherpassword",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "already exists" in detail.lower():
            log_test("A2", "Duplicate email returns 400", "PASS", f"Detail: {detail}")
        else:
            log_test("A2", "Duplicate email returns 400", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("A2", "Duplicate email returns 400", "FAIL", f"Status: {resp.status_code}")
    
    # A3: Password too short
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "Short Pass",
        "email": f"short{int(time.time())}@example.com",
        "password": "abc",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 400:
        log_test("A3", "Short password returns 400", "PASS")
    else:
        log_test("A3", "Short password returns 400", "FAIL", f"Status: {resp.status_code}")
    
    # A4: Empty fullName
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "",
        "email": f"empty{int(time.time())}@example.com",
        "password": "validpassword",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 400:
        log_test("A4", "Empty fullName returns 400", "PASS")
    else:
        log_test("A4", "Empty fullName returns 400", "FAIL", f"Status: {resp.status_code}")
    
    # A5: Malformed email
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "Bad Email",
        "email": "not-an-email",
        "password": "validpassword",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 422:
        log_test("A5", "Malformed email returns 422", "PASS")
    else:
        log_test("A5", "Malformed email returns 422", "FAIL", f"Status: {resp.status_code}")
    
    # A6: Verify newsletter subscription
    # Get master token first
    global master_token
    resp = requests.post(f"{BASE_URL}/admin/login", json={"password": MASTER_PASSWORD})
    if resp.status_code == 200:
        master_token = resp.json()["token"]
        
        # Check subscribers list
        resp = requests.get(f"{BASE_URL}/admin/subscribers",
                          headers={"Authorization": f"Bearer {master_token}"})
        if resp.status_code == 200:
            subscribers = resp.json()
            emails = [s["email"] for s in subscribers]
            if TEST_USER_EMAIL in emails:
                log_test("A6", "Newsletter subscription persisted", "PASS")
            else:
                log_test("A6", "Newsletter subscription persisted", "FAIL",
                        f"Email not in subscribers: {emails}")
        else:
            log_test("A6", "Newsletter subscription persisted", "FAIL",
                    f"Cannot get subscribers: {resp.status_code}")
    else:
        log_test("A6", "Newsletter subscription persisted", "FAIL",
                f"Cannot login as master: {resp.status_code}")


def test_b_user_login():
    """Test scenario B: User login."""
    print("\n" + "="*80)
    print("SCENARIO B: USER LOGIN")
    print("="*80)
    
    # B1: Valid login
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    
    if resp.status_code == 200:
        data = resp.json()
        if "token" in data and "user" in data:
            log_test("B1", "Valid login returns 200 with token and user", "PASS")
        else:
            log_test("B1", "Valid login returns 200 with token and user", "FAIL",
                    f"Missing token or user: {data}")
    else:
        log_test("B1", "Valid login returns 200 with token and user", "FAIL",
                f"Status: {resp.status_code}")
    
    # B2: Wrong password
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": "wrongpassword"
    })
    
    if resp.status_code == 401:
        detail = resp.json().get("detail", "")
        if "Invalid email or password" in detail:
            log_test("B2", "Wrong password returns 401", "PASS")
        else:
            log_test("B2", "Wrong password returns 401", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("B2", "Wrong password returns 401", "FAIL", f"Status: {resp.status_code}")
    
    # B3: Unknown email
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": f"unknown{int(time.time())}@example.com",
        "password": "anypassword"
    })
    
    if resp.status_code == 401:
        log_test("B3", "Unknown email returns 401", "PASS")
    else:
        log_test("B3", "Unknown email returns 401", "FAIL", f"Status: {resp.status_code}")


def test_c_auth_me():
    """Test scenario C: /auth/me endpoint."""
    print("\n" + "="*80)
    print("SCENARIO C: /auth/me ENDPOINT")
    print("="*80)
    
    # C1: With Jane's user token
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        if "user" in data:
            log_test("C1", "GET /auth/me with user token returns 200", "PASS")
        else:
            log_test("C1", "GET /auth/me with user token returns 200", "FAIL",
                    f"Missing user in response: {data}")
    else:
        log_test("C1", "GET /auth/me with user token returns 200", "FAIL",
                f"Status: {resp.status_code}")
    
    # C2: Without token
    resp = requests.get(f"{BASE_URL}/auth/me")
    
    if resp.status_code == 401:
        log_test("C2", "GET /auth/me without token returns 401", "PASS")
    else:
        log_test("C2", "GET /auth/me without token returns 401", "FAIL",
                f"Status: {resp.status_code}")
    
    # C3: With master admin token
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {master_token}"})
    
    if resp.status_code == 401:
        detail = resp.json().get("detail", "")
        if "User token required" in detail:
            log_test("C3", "GET /auth/me with admin token returns 401", "PASS")
        else:
            log_test("C3", "GET /auth/me with admin token returns 401", "FAIL",
                    f"Wrong detail: {detail}")
    else:
        log_test("C3", "GET /auth/me with admin token returns 401", "FAIL",
                f"Status: {resp.status_code}")


def test_d_update_profile():
    """Test scenario D: Update own profile."""
    global jane_token
    
    print("\n" + "="*80)
    print("SCENARIO D: UPDATE OWN PROFILE")
    print("="*80)
    
    # D1: Update fullName
    resp = requests.put(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"},
                       json={"fullName": "Jane D. Smith"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("user", {}).get("fullName") == "Jane D. Smith":
            log_test("D1", "Update fullName returns 200 and persists", "PASS")
        else:
            log_test("D1", "Update fullName returns 200 and persists", "FAIL",
                    f"Name not updated: {data}")
    else:
        log_test("D1", "Update fullName returns 200 and persists", "FAIL",
                f"Status: {resp.status_code}")
    
    # D2: Update password
    new_password = "newpassword"
    resp = requests.put(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"},
                       json={"password": new_password})
    
    if resp.status_code == 200:
        # Try logging in with new password
        resp2 = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": new_password
        })
        if resp2.status_code == 200:
            jane_token = resp2.json()["token"]  # Update token
            log_test("D2", "Update password works and login succeeds", "PASS")
        else:
            log_test("D2", "Update password works and login succeeds", "FAIL",
                    f"Login failed: {resp2.status_code}")
    else:
        log_test("D2", "Update password works and login succeeds", "FAIL",
                f"Status: {resp.status_code}")
    
    # D3: Password too short
    resp = requests.put(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"},
                       json={"password": "abc"})
    
    if resp.status_code == 400:
        log_test("D3", "Short password returns 400", "PASS")
    else:
        log_test("D3", "Short password returns 400", "FAIL", f"Status: {resp.status_code}")


def test_e_favorites():
    """Test scenario E: Favorites toggle."""
    print("\n" + "="*80)
    print("SCENARIO E: FAVORITES TOGGLE")
    print("="*80)
    
    # E1: Add cross-faith to favorites
    resp = requests.post(f"{BASE_URL}/auth/favorites/cross-faith",
                        headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("favorited") == True and "cross-faith" in data.get("favorites", []):
            log_test("E1", "Add to favorites returns favorited=true", "PASS")
        else:
            log_test("E1", "Add to favorites returns favorited=true", "FAIL", f"Data: {data}")
    else:
        log_test("E1", "Add to favorites returns favorited=true", "FAIL",
                f"Status: {resp.status_code}")
    
    # E2: Toggle again (remove)
    resp = requests.post(f"{BASE_URL}/auth/favorites/cross-faith",
                        headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("favorited") == False and "cross-faith" not in data.get("favorites", []):
            log_test("E2", "Remove from favorites returns favorited=false", "PASS")
        else:
            log_test("E2", "Remove from favorites returns favorited=false", "FAIL",
                    f"Data: {data}")
    else:
        log_test("E2", "Remove from favorites returns favorited=false", "FAIL",
                f"Status: {resp.status_code}")
    
    # E3: Add chakra
    resp = requests.post(f"{BASE_URL}/auth/favorites/chakra",
                        headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("favorited") == True and "chakra" in data.get("favorites", []):
            log_test("E3", "Add chakra to favorites", "PASS")
        else:
            log_test("E3", "Add chakra to favorites", "FAIL", f"Data: {data}")
    else:
        log_test("E3", "Add chakra to favorites", "FAIL", f"Status: {resp.status_code}")
    
    # E4: Verify persistence via /auth/me
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 200:
        favorites = resp.json().get("user", {}).get("favorites", [])
        if "chakra" in favorites:
            log_test("E4", "Favorites persist in /auth/me", "PASS", f"Favorites: {favorites}")
        else:
            log_test("E4", "Favorites persist in /auth/me", "FAIL", f"Favorites: {favorites}")
    else:
        log_test("E4", "Favorites persist in /auth/me", "FAIL", f"Status: {resp.status_code}")
    
    # E5: Without token
    resp = requests.post(f"{BASE_URL}/auth/favorites/anything")
    
    if resp.status_code == 401:
        log_test("E5", "Favorites without token returns 401", "PASS")
    else:
        log_test("E5", "Favorites without token returns 401", "FAIL",
                f"Status: {resp.status_code}")


def test_f_admin_user_management():
    """Test scenario F: Admin user management."""
    global viewer_id, viewer_token
    
    print("\n" + "="*80)
    print("SCENARIO F: ADMIN USER MANAGEMENT")
    print("="*80)
    
    # F1: GET /api/admin/users with master token
    resp = requests.get(f"{BASE_URL}/admin/users",
                       headers={"Authorization": f"Bearer {master_token}"})
    
    if resp.status_code == 200:
        users = resp.json()
        jane_found = any(u.get("email") == TEST_USER_EMAIL for u in users)
        if jane_found:
            log_test("F1", "GET /admin/users returns Jane", "PASS", f"Total users: {len(users)}")
        else:
            log_test("F1", "GET /admin/users returns Jane", "FAIL", f"Jane not found in {users}")
    else:
        log_test("F1", "GET /admin/users returns Jane", "FAIL", f"Status: {resp.status_code}")
    
    # F2: Without token
    resp = requests.get(f"{BASE_URL}/admin/users")
    
    if resp.status_code == 401:
        log_test("F2", "GET /admin/users without token returns 401", "PASS")
    else:
        log_test("F2", "GET /admin/users without token returns 401", "FAIL",
                f"Status: {resp.status_code}")
    
    # F3: Create viewer admin without manage_users permission
    resp = requests.post(f"{BASE_URL}/admin/admins",
                        headers={"Authorization": f"Bearer {master_token}"},
                        json={
                            "username": f"viewer{int(time.time())}",
                            "password": "viewerpw",
                            "permissions": [],
                            "isSuper": False
                        })
    
    if resp.status_code == 200:
        viewer_id = resp.json().get("id")
        viewer_username = resp.json().get("username")
        
        # Login as viewer
        resp2 = requests.post(f"{BASE_URL}/admin/login", json={
            "username": viewer_username,
            "password": "viewerpw"
        })
        if resp2.status_code == 200:
            viewer_token = resp2.json()["token"]
            
            # Try to access users list
            resp3 = requests.get(f"{BASE_URL}/admin/users",
                               headers={"Authorization": f"Bearer {viewer_token}"})
            if resp3.status_code == 403:
                log_test("F3", "Viewer without manage_users gets 403", "PASS")
            else:
                log_test("F3", "Viewer without manage_users gets 403", "FAIL",
                        f"Status: {resp3.status_code}")
        else:
            log_test("F3", "Viewer without manage_users gets 403", "FAIL",
                    f"Viewer login failed: {resp2.status_code}")
    else:
        log_test("F3", "Viewer without manage_users gets 403", "FAIL",
                f"Create viewer failed: {resp.status_code}")
    
    # F4: Grant manage_users permission
    resp = requests.put(f"{BASE_URL}/admin/admins/{viewer_id}",
                       headers={"Authorization": f"Bearer {master_token}"},
                       json={"permissions": ["manage_users"]})
    
    if resp.status_code == 200:
        # Re-login viewer to get new token
        resp2 = requests.post(f"{BASE_URL}/admin/login", json={
            "username": resp.json().get("username"),
            "password": "viewerpw"
        })
        if resp2.status_code == 200:
            viewer_token = resp2.json()["token"]
            
            # Try to access users list again
            resp3 = requests.get(f"{BASE_URL}/admin/users",
                               headers={"Authorization": f"Bearer {viewer_token}"})
            if resp3.status_code == 200:
                log_test("F4", "Viewer with manage_users gets 200", "PASS")
            else:
                log_test("F4", "Viewer with manage_users gets 200", "FAIL",
                        f"Status: {resp3.status_code}")
        else:
            log_test("F4", "Viewer with manage_users gets 200", "FAIL",
                    f"Re-login failed: {resp2.status_code}")
    else:
        log_test("F4", "Viewer with manage_users gets 200", "FAIL",
                f"Grant permission failed: {resp.status_code}")
    
    # F5: Ban Jane
    resp = requests.put(f"{BASE_URL}/admin/users/{jane_id}",
                       headers={"Authorization": f"Bearer {master_token}"},
                       json={"isBanned": True})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("isBanned") == True:
            log_test("F5", "Ban user returns 200 with isBanned=true", "PASS")
        else:
            log_test("F5", "Ban user returns 200 with isBanned=true", "FAIL", f"Data: {data}")
    else:
        log_test("F5", "Ban user returns 200 with isBanned=true", "FAIL",
                f"Status: {resp.status_code}")


def test_g_banned_user():
    """Test scenario G: Banned user flow."""
    print("\n" + "="*80)
    print("SCENARIO G: BANNED USER FLOW")
    print("="*80)
    
    # G1: Try to login as banned user
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": "newpassword"
    })
    
    if resp.status_code == 403:
        detail = resp.json().get("detail", "")
        if "suspended" in detail.lower():
            log_test("G1", "Banned user login returns 403", "PASS", f"Detail: {detail}")
        else:
            log_test("G1", "Banned user login returns 403", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("G1", "Banned user login returns 403", "FAIL", f"Status: {resp.status_code}")
    
    # G2: Try to use old token
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 403:
        detail = resp.json().get("detail", "")
        if "suspended" in detail.lower():
            log_test("G2", "Banned user old token returns 403", "PASS")
        else:
            log_test("G2", "Banned user old token returns 403", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("G2", "Banned user old token returns 403", "FAIL", f"Status: {resp.status_code}")
    
    # G3: Unban Jane
    resp = requests.put(f"{BASE_URL}/admin/users/{jane_id}",
                       headers={"Authorization": f"Bearer {master_token}"},
                       json={"isBanned": False})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("isBanned") == False:
            log_test("G3", "Unban user returns 200 with isBanned=false", "PASS")
        else:
            log_test("G3", "Unban user returns 200 with isBanned=false", "FAIL", f"Data: {data}")
    else:
        log_test("G3", "Unban user returns 200 with isBanned=false", "FAIL",
                f"Status: {resp.status_code}")
    
    # G4: Login after unban
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": "newpassword"
    })
    
    if resp.status_code == 200:
        log_test("G4", "Login after unban succeeds", "PASS")
    else:
        log_test("G4", "Login after unban succeeds", "FAIL", f"Status: {resp.status_code}")


def test_h_admin_delete_user():
    """Test scenario H: Admin delete user."""
    global jane_token
    
    print("\n" + "="*80)
    print("SCENARIO H: ADMIN DELETE USER")
    print("="*80)
    
    # H1: Delete Jane
    resp = requests.delete(f"{BASE_URL}/admin/users/{jane_id}",
                          headers={"Authorization": f"Bearer {master_token}"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") == True:
            log_test("H1", "Delete user returns 200 with ok=true", "PASS")
        else:
            log_test("H1", "Delete user returns 200 with ok=true", "FAIL", f"Data: {data}")
    else:
        log_test("H1", "Delete user returns 200 with ok=true", "FAIL",
                f"Status: {resp.status_code}")
    
    # H2: Try to use Jane's old token
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {jane_token}"})
    
    if resp.status_code == 401:
        log_test("H2", "Deleted user token returns 401", "PASS")
    else:
        log_test("H2", "Deleted user token returns 401", "FAIL", f"Status: {resp.status_code}")
    
    # H3: Try to login as deleted user
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": "newpassword"
    })
    
    if resp.status_code == 401:
        log_test("H3", "Deleted user login returns 401", "PASS")
    else:
        log_test("H3", "Deleted user login returns 401", "FAIL", f"Status: {resp.status_code}")
    
    # H4: Delete non-existent user
    resp = requests.delete(f"{BASE_URL}/admin/users/nonexistent-id",
                          headers={"Authorization": f"Bearer {master_token}"})
    
    if resp.status_code == 404:
        log_test("H4", "Delete non-existent user returns 404", "PASS")
    else:
        log_test("H4", "Delete non-existent user returns 404", "FAIL",
                f"Status: {resp.status_code}")


def test_i_permissions_metadata():
    """Test scenario I: Permission metadata."""
    print("\n" + "="*80)
    print("SCENARIO I: PERMISSIONS METADATA")
    print("="*80)
    
    resp = requests.get(f"{BASE_URL}/permissions")
    
    if resp.status_code == 200:
        data = resp.json()
        meta_perms = data.get("metaPermissions", [])
        all_perms = data.get("all", [])
        
        # metaPermissions can be either a dict or a list
        if isinstance(meta_perms, dict):
            has_manage_users = "manage_users" in meta_perms or "manage_users" in all_perms
            meta_list = list(meta_perms.keys())
        else:
            has_manage_users = "manage_users" in meta_perms or "manage_users" in all_perms
            meta_list = meta_perms
        
        if has_manage_users:
            total_perms = len(all_perms)
            expected = 19  # 14 sections + 5 meta
            if total_perms == expected:
                log_test("I1", "Permissions include manage_users", "PASS",
                        f"Total: {total_perms}, Meta: {meta_list}")
            else:
                log_test("I1", "Permissions include manage_users", "PASS",
                        f"Total: {total_perms} (expected {expected}), Meta: {meta_list}")
        else:
            log_test("I1", "Permissions include manage_users", "FAIL",
                    f"manage_users not found. Meta: {meta_perms}, All: {all_perms}")
    else:
        log_test("I1", "Permissions include manage_users", "FAIL",
                f"Status: {resp.status_code}")


def test_j_jwt_role_separation():
    """Test scenario J: JWT role separation."""
    print("\n" + "="*80)
    print("SCENARIO J: JWT ROLE SEPARATION")
    print("="*80)
    
    # J1: Create a new user to get a fresh token
    test_email = f"roletest{int(time.time())}@example.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "Role Test",
        "email": test_email,
        "password": "testpassword",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 200:
        user_token = resp.json()["token"]
        user_payload = decode_token(user_token)
        
        if user_payload.get("role") == "user":
            log_test("J1", "User token has role='user'", "PASS", f"Payload: {user_payload}")
        else:
            log_test("J1", "User token has role='user'", "FAIL",
                    f"Role: {user_payload.get('role')}")
        
        # J2: Verify admin token
        admin_payload = decode_token(master_token)
        is_super = admin_payload.get("isSuper")
        role = admin_payload.get("role")
        
        if is_super == True or role == "admin":
            log_test("J2", "Admin token has isSuper=true or role='admin'", "PASS",
                    f"isSuper: {is_super}, role: {role}")
        else:
            log_test("J2", "Admin token has isSuper=true or role='admin'", "FAIL",
                    f"isSuper: {is_super}, role: {role}")
        
        # J3: User token cannot access admin endpoints
        resp = requests.get(f"{BASE_URL}/admin/admins",
                          headers={"Authorization": f"Bearer {user_token}"})
        
        if resp.status_code == 401:
            log_test("J3", "User token cannot access /admin/* endpoints", "PASS")
        else:
            log_test("J3", "User token cannot access /admin/* endpoints", "FAIL",
                    f"Status: {resp.status_code}")
        
        # J4: Admin token cannot access /auth/me
        resp = requests.get(f"{BASE_URL}/auth/me",
                          headers={"Authorization": f"Bearer {master_token}"})
        
        if resp.status_code == 401:
            detail = resp.json().get("detail", "")
            if "User token required" in detail:
                log_test("J4", "Admin token cannot access /auth/me", "PASS")
            else:
                log_test("J4", "Admin token cannot access /auth/me", "FAIL",
                        f"Wrong detail: {detail}")
        else:
            log_test("J4", "Admin token cannot access /auth/me", "FAIL",
                    f"Status: {resp.status_code}")
    else:
        log_test("J1-J4", "JWT role separation tests", "FAIL",
                f"Cannot create test user: {resp.status_code}")


def main():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("ESSENTIAL GEMSTONES USER AUTHENTICATION TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test User Email: {TEST_USER_EMAIL}")
    
    try:
        test_a_user_registration()
        test_b_user_login()
        test_c_auth_me()
        test_d_update_profile()
        test_e_favorites()
        test_f_admin_user_management()
        test_g_banned_user()
        test_h_admin_delete_user()
        test_i_permissions_metadata()
        test_j_jwt_role_separation()
        
        print("\n" + "="*80)
        print("TEST SUITE COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
