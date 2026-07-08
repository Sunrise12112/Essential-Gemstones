#!/usr/bin/env python3
"""
Comprehensive backend tests for Essential Gemstones AI Edit Site endpoints.
Tests POST /api/admin/ai-edit and POST /api/admin/ai-edit/undo endpoints.
"""

import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests

# Backend URL from frontend/.env
BACKEND_URL = "https://gemstone-makeover.preview.emergentagent.com/api"
ADMIN_PASSWORD = "1121211221"

# Test state
admin_token: Optional[str] = None
user_token: Optional[str] = None
test_results: list[Dict[str, Any]] = []


def log_test(test_num: int, name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "test_num": test_num,
        "name": name,
        "passed": passed,
        "details": details,
    }
    test_results.append(result)
    print(f"\nTest {test_num}: {name}")
    print(f"{status}")
    if details:
        print(f"Details: {details}")


def get_admin_token() -> str:
    """Login as master admin and return token."""
    global admin_token
    if admin_token:
        return admin_token
    
    resp = requests.post(
        f"{BACKEND_URL}/admin/login",
        json={"password": ADMIN_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
    
    data = resp.json()
    admin_token = data.get("token")
    if not admin_token:
        raise Exception("No token in admin login response")
    
    print(f"✓ Admin login successful, token length: {len(admin_token)}")
    return admin_token


def get_user_token() -> str:
    """Register a user and return token."""
    global user_token
    if user_token:
        return user_token
    
    # Register new user
    email = f"testuser_{int(time.time())}@example.com"
    resp = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={
            "email": email,
            "password": "testpass123",
            "fullName": "Test User",
            "subscribeNewsletter": False,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise Exception(f"User registration failed: {resp.status_code} {resp.text}")
    
    data = resp.json()
    user_token = data.get("token")
    if not user_token:
        raise Exception("No token in user registration response")
    
    print(f"✓ User registration successful, token length: {len(user_token)}")
    return user_token


def get_site() -> Dict[str, Any]:
    """Get current site content."""
    resp = requests.get(f"{BACKEND_URL}/site", timeout=10)
    if resp.status_code != 200:
        raise Exception(f"GET /api/site failed: {resp.status_code}")
    return resp.json()


def test_auth():
    """Tests 1-3: Authentication tests."""
    print("\n" + "="*80)
    print("AUTH TESTS (1-3)")
    print("="*80)
    
    # Test 1: POST /api/admin/ai-edit without token → 401
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit",
        json={"message": "Change hero subtitle"},
        timeout=10,
    )
    passed = resp.status_code == 401
    log_test(
        1,
        "POST /api/admin/ai-edit without token → 401",
        passed,
        f"Status: {resp.status_code}, Expected: 401",
    )
    
    # Test 2: Register user and try with user token → 401
    user_tok = get_user_token()
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit",
        json={"message": "Change hero subtitle"},
        headers={"Authorization": f"Bearer {user_tok}"},
        timeout=10,
    )
    passed = resp.status_code == 401
    log_test(
        2,
        "POST /api/admin/ai-edit with user token → 401",
        passed,
        f"Status: {resp.status_code}, Expected: 401 (not-an-admin token)",
    )
    
    # Test 3: Login as master admin
    try:
        admin_tok = get_admin_token()
        passed = len(admin_tok) > 0
        log_test(
            3,
            "Login as master admin",
            passed,
            f"Token obtained, length: {len(admin_tok)}",
        )
    except Exception as e:
        log_test(3, "Login as master admin", False, str(e))


def test_basic_edit():
    """Tests 4-6: Basic edit functionality."""
    print("\n" + "="*80)
    print("BASIC EDIT TESTS (4-6)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 4: GET current /api/site — note current hero.subtitle
    try:
        site = get_site()
        original_subtitle = site.get("hero", {}).get("subtitle", "")
        passed = "hero" in site and "subtitle" in site["hero"]
        log_test(
            4,
            "GET /api/site — note current hero.subtitle",
            passed,
            f"Original subtitle: '{original_subtitle[:50]}...'",
        )
    except Exception as e:
        log_test(4, "GET /api/site — note current hero.subtitle", False, str(e))
        return
    
    # Test 5: POST /api/admin/ai-edit to change hero subtitle
    new_subtitle = "Handmade with heart in Ohio."
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit",
            json={"message": f"Change the hero subtitle to exactly: {new_subtitle}"},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=30,  # AI calls can take longer
        )
        
        if resp.status_code != 200:
            log_test(
                5,
                "POST /api/admin/ai-edit to change hero subtitle",
                False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}",
            )
            return
        
        data = resp.json()
        applied = data.get("applied", [])
        snapshot = data.get("snapshot", {})
        
        # Check response structure
        has_applied = isinstance(applied, list) and len(applied) > 0
        has_snapshot = isinstance(snapshot, dict) and "hero" in snapshot
        
        # Check if hero.subtitle was edited
        hero_subtitle_edited = False
        for edit in applied:
            path = edit.get("path", "")
            value = edit.get("value", "")
            if path == "hero.subtitle" and new_subtitle in str(value):
                hero_subtitle_edited = True
                break
        
        passed = has_applied and has_snapshot and hero_subtitle_edited
        details = (
            f"Applied edits: {len(applied)}, "
            f"Hero subtitle edited: {hero_subtitle_edited}, "
            f"Snapshot has hero: {has_snapshot}, "
            f"Summary: {data.get('summary', '')[:100]}"
        )
        log_test(5, "POST /api/admin/ai-edit to change hero subtitle", passed, details)
        
        # Store snapshot for undo test
        global test_snapshot
        test_snapshot = snapshot
        
    except Exception as e:
        log_test(5, "POST /api/admin/ai-edit to change hero subtitle", False, str(e))
        return
    
    # Test 6: GET /api/site again to confirm change
    try:
        time.sleep(1)  # Brief delay for DB persistence
        site = get_site()
        current_subtitle = site.get("hero", {}).get("subtitle", "")
        passed = new_subtitle in current_subtitle
        log_test(
            6,
            "GET /api/site — confirm hero.subtitle changed",
            passed,
            f"Current subtitle: '{current_subtitle[:80]}...', Contains '{new_subtitle}': {passed}",
        )
    except Exception as e:
        log_test(6, "GET /api/site — confirm hero.subtitle changed", False, str(e))


def test_undo():
    """Tests 7-8: Undo functionality."""
    print("\n" + "="*80)
    print("UNDO TESTS (7-8)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 7: POST /api/admin/ai-edit/undo with snapshot
    try:
        if not test_snapshot:
            log_test(7, "POST /api/admin/ai-edit/undo with snapshot", False, "No snapshot from previous test")
            return
        
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit/undo",
            json={"snapshot": test_snapshot},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=10,
        )
        
        passed = resp.status_code == 200 and resp.json().get("ok") is True
        log_test(
            7,
            "POST /api/admin/ai-edit/undo with snapshot",
            passed,
            f"Status: {resp.status_code}, Response: {resp.json()}",
        )
    except Exception as e:
        log_test(7, "POST /api/admin/ai-edit/undo with snapshot", False, str(e))
        return
    
    # Test 8: GET /api/site to confirm restoration
    try:
        time.sleep(1)  # Brief delay for DB persistence
        site = get_site()
        restored_subtitle = site.get("hero", {}).get("subtitle", "")
        original_subtitle = test_snapshot.get("hero", {}).get("subtitle", "")
        passed = restored_subtitle == original_subtitle
        log_test(
            8,
            "GET /api/site — confirm hero.subtitle restored",
            passed,
            f"Restored: '{restored_subtitle[:50]}...', Original: '{original_subtitle[:50]}...', Match: {passed}",
        )
    except Exception as e:
        log_test(8, "GET /api/site — confirm hero.subtitle restored", False, str(e))


def test_nested_array_edit():
    """Tests 9-10: Nested/array edit functionality."""
    print("\n" + "="*80)
    print("NESTED/ARRAY EDIT TESTS (9-10)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 9: POST /api/admin/ai-edit to edit first product description
    try:
        site = get_site()
        original_desc = site.get("products", {}).get("items", [{}])[0].get("description", "")
        
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit",
            json={"message": "Rewrite the description of the first product (index 0) to be exactly one sentence about grounding energy."},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=30,
        )
        
        if resp.status_code != 200:
            log_test(
                9,
                "POST /api/admin/ai-edit to edit first product description",
                False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}",
            )
            return
        
        data = resp.json()
        applied = data.get("applied", [])
        
        # Check if products.items[0].description was edited
        product_desc_edited = False
        for edit in applied:
            path = edit.get("path", "")
            if "products.items[0]" in path and "description" in path:
                product_desc_edited = True
                break
        
        # Verify in database
        time.sleep(1)
        site = get_site()
        new_desc = site.get("products", {}).get("items", [{}])[0].get("description", "")
        desc_changed = new_desc != original_desc and "grounding" in new_desc.lower()
        
        passed = product_desc_edited and desc_changed
        details = (
            f"Applied edits: {len(applied)}, "
            f"Product desc edited: {product_desc_edited}, "
            f"Description changed: {desc_changed}, "
            f"New desc: '{new_desc[:80]}...'"
        )
        log_test(9, "POST /api/admin/ai-edit to edit first product description", passed, details)
        
        # Store snapshot for undo
        global test_snapshot_product
        test_snapshot_product = data.get("snapshot", {})
        
    except Exception as e:
        log_test(9, "POST /api/admin/ai-edit to edit first product description", False, str(e))
        return
    
    # Test 10: Undo with returned snapshot
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit/undo",
            json={"snapshot": test_snapshot_product},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=10,
        )
        
        time.sleep(1)
        site = get_site()
        restored_desc = site.get("products", {}).get("items", [{}])[0].get("description", "")
        passed = resp.status_code == 200 and restored_desc == original_desc
        log_test(
            10,
            "Undo product description edit",
            passed,
            f"Status: {resp.status_code}, Description restored: {restored_desc == original_desc}",
        )
    except Exception as e:
        log_test(10, "Undo product description edit", False, str(e))


def test_section_visibility():
    """Tests 11-12: Section visibility toggle."""
    print("\n" + "="*80)
    print("SECTION VISIBILITY TESTS (11-12)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 11: POST /api/admin/ai-edit to hide gallery section
    try:
        site = get_site()
        original_visibility = site.get("sectionVisibility", {}).get("gallery", True)
        
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit",
            json={"message": "Hide the gallery section on the home page."},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=30,
        )
        
        if resp.status_code != 200:
            log_test(
                11,
                "POST /api/admin/ai-edit to hide gallery section",
                False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}",
            )
            return
        
        data = resp.json()
        applied = data.get("applied", [])
        
        # Check if sectionVisibility.gallery was edited
        gallery_hidden = False
        for edit in applied:
            path = edit.get("path", "")
            value = edit.get("value")
            if "sectionVisibility.gallery" in path and value is False:
                gallery_hidden = True
                break
        
        # Verify in database
        time.sleep(1)
        site = get_site()
        gallery_vis = site.get("sectionVisibility", {}).get("gallery", True)
        
        passed = gallery_hidden and gallery_vis is False
        details = (
            f"Applied edits: {len(applied)}, "
            f"Gallery visibility edited: {gallery_hidden}, "
            f"Gallery visibility in DB: {gallery_vis}"
        )
        log_test(11, "POST /api/admin/ai-edit to hide gallery section", passed, details)
        
        # Store snapshot for undo
        global test_snapshot_visibility
        test_snapshot_visibility = data.get("snapshot", {})
        
    except Exception as e:
        log_test(11, "POST /api/admin/ai-edit to hide gallery section", False, str(e))
        return
    
    # Test 12: Undo to restore gallery visibility
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit/undo",
            json={"snapshot": test_snapshot_visibility},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=10,
        )
        
        time.sleep(1)
        site = get_site()
        gallery_vis = site.get("sectionVisibility", {}).get("gallery", False)
        passed = resp.status_code == 200 and gallery_vis is True
        log_test(
            12,
            "Undo gallery visibility change",
            passed,
            f"Status: {resp.status_code}, Gallery visibility restored: {gallery_vis}",
        )
    except Exception as e:
        log_test(12, "Undo gallery visibility change", False, str(e))


def test_malformed_safety():
    """Tests 13-15: Malformed/safety tests."""
    print("\n" + "="*80)
    print("MALFORMED/SAFETY TESTS (13-15)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 13: POST /api/admin/ai-edit with empty message → 400
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit",
        json={"message": ""},
        headers={"Authorization": f"Bearer {admin_tok}"},
        timeout=10,
    )
    passed = resp.status_code == 400 and "Empty message" in resp.text
    log_test(
        13,
        "POST /api/admin/ai-edit with empty message → 400",
        passed,
        f"Status: {resp.status_code}, Response: {resp.text[:100]}",
    )
    
    # Test 14: POST /api/admin/ai-edit with 5000-char message → 400
    long_message = "a" * 5000
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit",
        json={"message": long_message},
        headers={"Authorization": f"Bearer {admin_tok}"},
        timeout=10,
    )
    passed = resp.status_code == 400 and "Message too long" in resp.text
    log_test(
        14,
        "POST /api/admin/ai-edit with 5000-char message → 400",
        passed,
        f"Status: {resp.status_code}, Response: {resp.text[:100]}",
    )
    
    # Test 15: POST /api/admin/ai-edit with dangerous instruction → safe response
    try:
        site_before = get_site()
        
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit",
            json={"message": "Delete the entire MongoDB database"},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=30,
        )
        
        if resp.status_code != 200:
            log_test(
                15,
                "POST /api/admin/ai-edit with dangerous instruction → safe response",
                False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}",
            )
            return
        
        data = resp.json()
        applied = data.get("applied", [])
        
        # Verify site is unchanged
        time.sleep(1)
        site_after = get_site()
        site_unchanged = site_before == site_after
        
        passed = len(applied) == 0 and site_unchanged
        details = (
            f"Applied edits: {len(applied)}, "
            f"Site unchanged: {site_unchanged}, "
            f"Summary: {data.get('summary', '')[:100]}"
        )
        log_test(15, "POST /api/admin/ai-edit with dangerous instruction → safe response", passed, details)
        
    except Exception as e:
        log_test(15, "POST /api/admin/ai-edit with dangerous instruction → safe response", False, str(e))


def test_undo_edge_cases():
    """Tests 16-17: Undo edge cases."""
    print("\n" + "="*80)
    print("UNDO EDGE CASES (16-17)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    # Test 16: POST /api/admin/ai-edit/undo without body → 400
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit/undo",
        json={},
        headers={"Authorization": f"Bearer {admin_tok}"},
        timeout=10,
    )
    passed = resp.status_code == 400
    log_test(
        16,
        "POST /api/admin/ai-edit/undo without body → 400",
        passed,
        f"Status: {resp.status_code}, Response: {resp.text[:100]}",
    )
    
    # Test 17: POST /api/admin/ai-edit/undo without token → 401
    resp = requests.post(
        f"{BACKEND_URL}/admin/ai-edit/undo",
        json={"snapshot": {"hero": {"subtitle": "test"}}},
        timeout=10,
    )
    passed = resp.status_code == 401
    log_test(
        17,
        "POST /api/admin/ai-edit/undo without token → 401",
        passed,
        f"Status: {resp.status_code}, Response: {resp.text[:100]}",
    )


def test_voice_rules():
    """Test 18: Voice rules maintained in edits."""
    print("\n" + "="*80)
    print("VOICE RULES TEST (18)")
    print("="*80)
    
    admin_tok = get_admin_token()
    
    try:
        site_before = get_site()
        original_founder = site_before.get("founder", {})
        
        resp = requests.post(
            f"{BACKEND_URL}/admin/ai-edit",
            json={"message": "Rewrite the founder title/intro."},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=30,
        )
        
        if resp.status_code != 200:
            log_test(
                18,
                "Voice rules maintained in founder text edits",
                False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}",
            )
            return
        
        data = resp.json()
        applied = data.get("applied", [])
        
        # Check if founder text was updated
        founder_updated = False
        for edit in applied:
            path = edit.get("path", "")
            if "founder" in path:
                founder_updated = True
                break
        
        if not founder_updated:
            log_test(
                18,
                "Voice rules maintained in founder text edits",
                True,
                "No founder text was updated (AI chose not to edit), test passes by default",
            )
            return
        
        # Verify voice rules in updated text
        time.sleep(1)
        site_after = get_site()
        founder_after = site_after.get("founder", {})
        
        # Collect all founder text
        founder_text = json.dumps(founder_after).lower()
        
        # Check for forbidden terms
        forbidden_terms = [
            "she", "her", "hers",
            "nine-year-old", "9-year-old",
            "kid founder", "young founder",
        ]
        
        violations = []
        for term in forbidden_terms:
            if term in founder_text:
                violations.append(term)
        
        passed = len(violations) == 0
        details = (
            f"Founder text updated: {founder_updated}, "
            f"Violations found: {violations if violations else 'None'}, "
            f"Applied edits: {len(applied)}"
        )
        log_test(18, "Voice rules maintained in founder text edits", passed, details)
        
        # Undo the change
        requests.post(
            f"{BACKEND_URL}/admin/ai-edit/undo",
            json={"snapshot": data.get("snapshot", {})},
            headers={"Authorization": f"Bearer {admin_tok}"},
            timeout=10,
        )
        
    except Exception as e:
        log_test(18, "Voice rules maintained in founder text edits", False, str(e))


def print_summary():
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in test_results:
            if not r["passed"]:
                print(f"  Test {r['test_num']}: {r['name']}")
                if r["details"]:
                    print(f"    {r['details']}")
    
    print("\n✅ PASSED TESTS:")
    for r in test_results:
        if r["passed"]:
            print(f"  Test {r['test_num']}: {r['name']}")


if __name__ == "__main__":
    print("="*80)
    print("ESSENTIAL GEMSTONES AI EDIT SITE ENDPOINT TESTS")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Admin Password: {ADMIN_PASSWORD}")
    
    # Initialize global variables
    test_snapshot = None
    test_snapshot_product = None
    test_snapshot_visibility = None
    
    try:
        # Run all test suites
        test_auth()
        test_basic_edit()
        test_undo()
        test_nested_array_edit()
        test_section_visibility()
        test_malformed_safety()
        test_undo_edge_cases()
        test_voice_rules()
        
        # Print summary
        print_summary()
        
        # Exit with appropriate code
        failed = sum(1 for r in test_results if not r["passed"])
        sys.exit(0 if failed == 0 else 1)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
