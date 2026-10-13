"""Backend tests for admin SMS 2FA (email removed, SMS added, luca renamed).

CRITICAL: Do NOT call POST /api/admin/2fa/sms/send -- sends real SMS.
"""
import os
import pyotp
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gemstone-makeover.preview.emergentagent.com").rstrip("/")
USERNAME = "luca"
PASSWORD = "1121211221"
TOTP_SECRET = "IVQKJZDYWPOQ4ZAXNKMNU22TQ5N5DL7U"


@pytest.fixture(scope="module")
def login_pre_2fa():
    r = requests.post(f"{BASE_URL}/api/admin/login", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "needs_2fa", data
    return data


def test_admin_login_needs_2fa_sms_available(login_pre_2fa):
    data = login_pre_2fa
    assert "twoFactorToken" in data
    methods = data.get("availableMethods") or []
    assert "totp" in methods
    assert "sms" in methods
    assert "email" not in methods, f"email method should be removed, got {methods}"
    assert data.get("phoneHint", "").endswith("1745"), data.get("phoneHint")


def test_old_email_send_endpoint_removed(login_pre_2fa):
    tft = login_pre_2fa["twoFactorToken"]
    r = requests.post(
        f"{BASE_URL}/api/admin/2fa/email/send",
        json={"twoFactorToken": tft},
        headers={"Authorization": f"Bearer {tft}"},
    )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text[:200]}"


def test_methods_endpoint_shape(login_pre_2fa):
    tft = login_pre_2fa["twoFactorToken"]
    r = requests.get(
        f"{BASE_URL}/api/admin/2fa/methods",
        headers={"Authorization": f"Bearer {tft}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    methods = body.get("methods") or []
    assert "totp" in methods
    assert "sms" in methods
    assert "email" not in methods
    assert body.get("phoneHint", "").endswith("1745")


@pytest.fixture(scope="module")
def admin_jwt():
    r = requests.post(f"{BASE_URL}/api/admin/login", json={"username": USERNAME, "password": PASSWORD})
    data = r.json()
    tft = data["twoFactorToken"]
    code = pyotp.TOTP(TOTP_SECRET).now()
    r2 = requests.post(
        f"{BASE_URL}/api/admin/2fa/login",
        json={"twoFactorToken": tft, "code": code, "method": "totp"},
        headers={"Authorization": f"Bearer {tft}"},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert "token" in body
    return body["token"]


def test_totp_login_and_dashboard_access(admin_jwt):
    assert admin_jwt
    r = requests.get(f"{BASE_URL}/api/admin/me", headers={"Authorization": f"Bearer {admin_jwt}"})
    # /api/admin/me may or may not exist; try admins list for super
    if r.status_code == 404:
        r = requests.get(f"{BASE_URL}/api/admin/admins", headers={"Authorization": f"Bearer {admin_jwt}"})
    assert r.status_code == 200, r.text


def test_create_admin_requires_phone_no_email(admin_jwt):
    headers = {"Authorization": f"Bearer {admin_jwt}"}
    # Missing phone -> should fail validation
    r = requests.post(
        f"{BASE_URL}/api/admin/admins",
        json={"username": "TEST_nophone", "password": "Aa1!aaaa", "isSuper": False, "permissions": ["manageProducts"]},
        headers=headers,
    )
    assert r.status_code in (400, 422), f"Expected validation error, got {r.status_code}: {r.text[:200]}"


def test_create_edit_delete_phonetest_admin(admin_jwt):
    headers = {"Authorization": f"Bearer {admin_jwt}"}
    # Clean up any existing TEST_ admins named phonetest
    r = requests.get(f"{BASE_URL}/api/admin/admins", headers=headers)
    assert r.status_code == 200
    existing = r.json() if isinstance(r.json(), list) else r.json().get("admins", [])
    for a in existing:
        if a.get("username") in ("phonetest", "TEST_phonetest"):
            aid = a.get("id") or a.get("_id")
            requests.delete(f"{BASE_URL}/api/admin/admins/{aid}", headers=headers)

    # Create
    create_payload = {
        "username": "phonetest",
        "password": "Aa1!aaaa",
        "phone": "5551234567",
        "isSuper": False,
        "permissions": ["manageProducts"],
    }
    r = requests.post(f"{BASE_URL}/api/admin/admins", json=create_payload, headers=headers)
    assert r.status_code in (200, 201), r.text
    created = r.json()
    admin_id = created.get("id") or created.get("_id")
    assert admin_id
    assert created.get("phone") == "5551234567"

    # Verify in list
    r = requests.get(f"{BASE_URL}/api/admin/admins", headers=headers)
    lst = r.json() if isinstance(r.json(), list) else r.json().get("admins", [])
    found = next((a for a in lst if (a.get("id") or a.get("_id")) == admin_id), None)
    assert found is not None
    assert found.get("phone") == "5551234567"

    # Edit phone
    r = requests.patch(
        f"{BASE_URL}/api/admin/admins/{admin_id}",
        json={"phone": "5559876543"},
        headers=headers,
    )
    if r.status_code == 405 or r.status_code == 404:
        r = requests.put(
            f"{BASE_URL}/api/admin/admins/{admin_id}",
            json={"phone": "5559876543"},
            headers=headers,
        )
    assert r.status_code in (200, 204), r.text

    # Verify updated
    r = requests.get(f"{BASE_URL}/api/admin/admins", headers=headers)
    lst = r.json() if isinstance(r.json(), list) else r.json().get("admins", [])
    found = next((a for a in lst if (a.get("id") or a.get("_id")) == admin_id), None)
    assert found.get("phone") == "5559876543"

    # Delete cleanup
    r = requests.delete(f"{BASE_URL}/api/admin/admins/{admin_id}", headers=headers)
    assert r.status_code in (200, 204), r.text
