#!/usr/bin/env python3
"""
Essential Gemstones CMS Backend Test Suite
Tests all backend endpoints as specified in the review request.
"""
import io
import json
import os
import sys
from pathlib import Path

import requests

# Read BACKEND_URL from frontend .env
frontend_env = Path("/app/frontend/.env")
BACKEND_URL = None
if frontend_env.exists():
    with open(frontend_env) as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BACKEND_URL = line.split("=", 1)[1].strip()
                break

if not BACKEND_URL:
    print("❌ ERROR: Could not read REACT_APP_BACKEND_URL from /app/frontend/.env")
    sys.exit(1)

print(f"🔗 Testing backend at: {BACKEND_URL}")
print("=" * 80)

# Test results tracking
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test_result(test_name, passed, message=""):
    """Record test result"""
    if passed:
        results["passed"].append(test_name)
        print(f"✅ {test_name}")
        if message:
            print(f"   {message}")
    else:
        results["failed"].append(test_name)
        print(f"❌ {test_name}")
        if message:
            print(f"   {message}")

def test_warning(test_name, message):
    """Record test warning"""
    results["warnings"].append(test_name)
    print(f"⚠️  {test_name}")
    print(f"   {message}")

# Global token storage
admin_token = None
uploaded_file_url = None

print("\n📋 TEST 1: GET /api/ - Root endpoint")
print("-" * 80)
try:
    response = requests.get(f"{BACKEND_URL}/api/", timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get("message") == "Essential Gemstones API":
            test_result("Test 1: Root endpoint", True, f"Response: {data}")
        else:
            test_result("Test 1: Root endpoint", False, f"Unexpected response: {data}")
    else:
        test_result("Test 1: Root endpoint", False, f"Status: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Test 1: Root endpoint", False, f"Exception: {str(e)}")

print("\n📋 TEST 2: GET /api/site - Public site content (auto-seed)")
print("-" * 80)
try:
    response = requests.get(f"{BACKEND_URL}/api/site", timeout=10)
    if response.status_code == 200:
        data = response.json()
        expected_keys = [
            "navbar", "hero", "products", "story", "promise", "chakra", 
            "stats", "lavaMeaning", "founder", "craft", "faq", "gallery", 
            "vip", "footer", "sectionOrder", "sectionVisibility"
        ]
        missing_keys = [k for k in expected_keys if k not in data]
        if not missing_keys:
            test_result("Test 2: GET /api/site", True, f"All {len(expected_keys)} expected keys present")
            # Verify sectionOrder has 12 items
            section_order = data.get("sectionOrder", [])
            if len(section_order) == 12:
                print(f"   ✓ sectionOrder has 12 items: {section_order}")
            else:
                test_warning("Test 2: sectionOrder length", f"Expected 12 items, got {len(section_order)}: {section_order}")
        else:
            test_result("Test 2: GET /api/site", False, f"Missing keys: {missing_keys}")
    else:
        test_result("Test 2: GET /api/site", False, f"Status: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Test 2: GET /api/site", False, f"Exception: {str(e)}")

print("\n📋 TEST 3: POST /api/admin/login - Valid password")
print("-" * 80)
try:
    response = requests.post(
        f"{BACKEND_URL}/api/admin/login",
        json={"password": "1121211221"},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if "token" in data:
            admin_token = data["token"]
            test_result("Test 3: Admin login (valid)", True, f"Token received (length: {len(admin_token)})")
        else:
            test_result("Test 3: Admin login (valid)", False, f"No token in response: {data}")
    else:
        test_result("Test 3: Admin login (valid)", False, f"Status: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Test 3: Admin login (valid)", False, f"Exception: {str(e)}")

print("\n📋 TEST 4: POST /api/admin/login - Invalid password")
print("-" * 80)
try:
    response = requests.post(
        f"{BACKEND_URL}/api/admin/login",
        json={"password": "wrong"},
        timeout=10
    )
    if response.status_code == 401:
        test_result("Test 4: Admin login (invalid)", True, f"Correctly returned 401")
    else:
        test_result("Test 4: Admin login (invalid)", False, f"Expected 401, got {response.status_code}")
except Exception as e:
    test_result("Test 4: Admin login (invalid)", False, f"Exception: {str(e)}")

print("\n📋 TEST 5: GET /api/admin/me - Without token")
print("-" * 80)
try:
    response = requests.get(f"{BACKEND_URL}/api/admin/me", timeout=10)
    if response.status_code == 401:
        test_result("Test 5: Admin /me (no token)", True, f"Correctly returned 401")
    else:
        test_result("Test 5: Admin /me (no token)", False, f"Expected 401, got {response.status_code}")
except Exception as e:
    test_result("Test 5: Admin /me (no token)", False, f"Exception: {str(e)}")

print("\n📋 TEST 6: GET /api/admin/me - With valid token")
print("-" * 80)
if admin_token:
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BACKEND_URL}/api/admin/me", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") is True:
                test_result("Test 6: Admin /me (with token)", True, f"Response: {data}")
            else:
                test_result("Test 6: Admin /me (with token)", False, f"Unexpected response: {data}")
        else:
            test_result("Test 6: Admin /me (with token)", False, f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        test_result("Test 6: Admin /me (with token)", False, f"Exception: {str(e)}")
else:
    test_result("Test 6: Admin /me (with token)", False, "No admin token available from Test 3")

print("\n📋 TEST 7: PUT /api/site - Without token")
print("-" * 80)
try:
    response = requests.put(
        f"{BACKEND_URL}/api/site",
        json={"hero": {"kicker": "Test Update"}},
        timeout=10
    )
    if response.status_code == 401:
        test_result("Test 7: PUT /api/site (no token)", True, f"Correctly returned 401")
    else:
        test_result("Test 7: PUT /api/site (no token)", False, f"Expected 401, got {response.status_code}")
except Exception as e:
    test_result("Test 7: PUT /api/site (no token)", False, f"Exception: {str(e)}")

print("\n📋 TEST 8: PUT /api/site - With token and verify persistence")
print("-" * 80)
if admin_token:
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        test_kicker = f"Test Update {os.urandom(4).hex()}"
        update_payload = {
            "hero": {
                "kicker": test_kicker,
                "titleLine1": "Essential",
                "titleLine2": "Gemstones",
                "subtitle": "Test subtitle",
                "ctaPrimary": {"label": "Shop", "href": "#shop"},
                "ctaSecondary": {"label": "Story", "href": "#story"},
                "mediaType": "image",
                "mediaUrl": "https://example.com/test.jpg",
                "quoteText": "Test quote",
                "quoteAuthor": "Test Author"
            }
        }
        
        # Update
        response = requests.put(
            f"{BACKEND_URL}/api/site",
            json=update_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("hero", {}).get("kicker") == test_kicker:
                print(f"   ✓ Update successful, kicker set to: {test_kicker}")
                
                # Verify persistence by fetching again
                verify_response = requests.get(f"{BACKEND_URL}/api/site", timeout=10)
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if verify_data.get("hero", {}).get("kicker") == test_kicker:
                        test_result("Test 8: PUT /api/site (with token)", True, f"Update persisted correctly")
                    else:
                        test_result("Test 8: PUT /api/site (with token)", False, 
                                  f"Update not persisted. Expected: {test_kicker}, Got: {verify_data.get('hero', {}).get('kicker')}")
                else:
                    test_result("Test 8: PUT /api/site (with token)", False, 
                              f"Verification GET failed with status {verify_response.status_code}")
            else:
                test_result("Test 8: PUT /api/site (with token)", False, 
                          f"Update response incorrect. Expected kicker: {test_kicker}, Got: {data.get('hero', {}).get('kicker')}")
        else:
            test_result("Test 8: PUT /api/site (with token)", False, 
                      f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        test_result("Test 8: PUT /api/site (with token)", False, f"Exception: {str(e)}")
else:
    test_result("Test 8: PUT /api/site (with token)", False, "No admin token available from Test 3")

print("\n📋 TEST 9: POST /api/upload - Without token")
print("-" * 80)
try:
    # Create a small test image
    test_image = io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
    files = {"file": ("test.png", test_image, "image/png")}
    
    response = requests.post(f"{BACKEND_URL}/api/upload", files=files, timeout=10)
    if response.status_code == 401:
        test_result("Test 9: POST /api/upload (no token)", True, f"Correctly returned 401")
    else:
        test_result("Test 9: POST /api/upload (no token)", False, f"Expected 401, got {response.status_code}")
except Exception as e:
    test_result("Test 9: POST /api/upload (no token)", False, f"Exception: {str(e)}")

print("\n📋 TEST 10: POST /api/upload - With token and verify file retrieval")
print("-" * 80)
if admin_token:
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Create a small test PNG image (1x1 pixel)
        test_image = io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        files = {"file": ("test_gemstone.png", test_image, "image/png")}
        
        response = requests.post(
            f"{BACKEND_URL}/api/upload",
            files=files,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "url" in data and "kind" in data and "size" in data:
                uploaded_file_url = data["url"]
                print(f"   ✓ Upload successful: {data}")
                
                # Verify file retrieval
                file_url = f"{BACKEND_URL}{uploaded_file_url}"
                file_response = requests.get(file_url, timeout=10)
                
                if file_response.status_code == 200:
                    if len(file_response.content) > 0:
                        test_result("Test 10: POST /api/upload (with token)", True, 
                                  f"File uploaded and retrieved successfully ({len(file_response.content)} bytes)")
                    else:
                        test_result("Test 10: POST /api/upload (with token)", False, 
                                  f"File retrieved but empty")
                else:
                    test_result("Test 10: POST /api/upload (with token)", False, 
                              f"File upload succeeded but retrieval failed with status {file_response.status_code}")
            else:
                test_result("Test 10: POST /api/upload (with token)", False, 
                          f"Missing expected fields in response: {data}")
        else:
            test_result("Test 10: POST /api/upload (with token)", False, 
                      f"Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        test_result("Test 10: POST /api/upload (with token)", False, f"Exception: {str(e)}")
else:
    test_result("Test 10: POST /api/upload (with token)", False, "No admin token available from Test 3")

print("\n📋 TEST 11: POST /api/upload - Unsupported file type")
print("-" * 80)
if admin_token:
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Create a text file
        test_file = io.BytesIO(b'This is a test text file')
        files = {"file": ("test.txt", test_file, "text/plain")}
        
        response = requests.post(
            f"{BACKEND_URL}/api/upload",
            files=files,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 400:
            test_result("Test 11: POST /api/upload (unsupported type)", True, 
                      f"Correctly returned 400 for .txt file")
        else:
            test_result("Test 11: POST /api/upload (unsupported type)", False, 
                      f"Expected 400, got {response.status_code}")
    except Exception as e:
        test_result("Test 11: POST /api/upload (unsupported type)", False, f"Exception: {str(e)}")
else:
    test_result("Test 11: POST /api/upload (unsupported type)", False, "No admin token available from Test 3")

# Print summary
print("\n" + "=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)
print(f"✅ Passed: {len(results['passed'])}")
for test in results['passed']:
    print(f"   • {test}")

if results['warnings']:
    print(f"\n⚠️  Warnings: {len(results['warnings'])}")
    for test in results['warnings']:
        print(f"   • {test}")

if results['failed']:
    print(f"\n❌ Failed: {len(results['failed'])}")
    for test in results['failed']:
        print(f"   • {test}")
    print("\n🔴 OVERALL: TESTS FAILED")
    sys.exit(1)
else:
    print("\n🟢 OVERALL: ALL TESTS PASSED")
    sys.exit(0)
