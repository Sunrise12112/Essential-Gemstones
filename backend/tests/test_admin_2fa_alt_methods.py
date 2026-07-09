"""Backend tests for the ALTERNATIVE 2FA methods added on top of TOTP.

Covers:
- /api/admin/login now includes availableMethods + emailHint after password OK on 2FA-enabled admin.
- /api/admin/2fa/methods (GET) with challenge Bearer.
- /api/admin/2fa/email/send: sends OTP, rate limit (30s), sentTo obfuscated, stores hashed row.
- /api/admin/2fa/login with method="email" + injected known OTP row → success.
- /api/admin/2fa/login wrong email code → 401. After 5 wrong attempts row is deleted; further attempts fail.
- /api/admin/2fa/login with method="totp" + valid TOTP.
- trustDevice=true issues trustDeviceToken + trustDeviceDays.
- X-Admin-Trust-Token header on /api/admin/login skips 2FA (status ok, trustedDevice=true).
- /api/admin/trusted-devices GET list, DELETE {id}, DELETE (all).
- /api/admin/2fa/disable purges trusted devices.
- /api/admin/2fa/reset/{admin_id} purges trusted devices + email otps.
- Auto-detect fallback: /api/admin/2fa/login without `method` accepts TOTP & backup codes (regression).
- Regression: /api/admin/2fa/setup, /enable, /backup-codes/regenerate still work.
"""
import os
import time
import uuid
from datetime import datetime, timedelta

import pymongo
import pyotp
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gemstone-makeover.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MASTER_USER = "master"
MASTER_PW = "1121211221"
STRONG_PW = "Aa1!aaaa"

# We reuse the same password hasher constants as backend: hash_password uses bcrypt.
# For the email-OTP-success test we insert a KNOWN OTP hash directly into Mongo.
import bcrypt


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _mongo():
    return pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[
        os.environ.get("DB_NAME", "test_database")
    ]


def _wipe_master_2fa():
    db = _mongo()
    db.admins.update_one(
        {"username": "master"},
        {
            "$unset": {
                "twoFactorSecret": "",
                "twoFactorEnabled": "",
                "twoFactorBackupCodes": "",
                "twoFactorPendingSecret": "",
                "twoFactorEnabledAt": "",
            }
        },
    )
    db.admin_trusted_devices.delete_many({})
    db.admin_email_otps.delete_many({})


def _cleanup_test_admins():
    db = _mongo()
    ids = [d["_id"] for d in db.admins.find({"username": {"$regex": "^test_"}}, {"_id": 1})]
    if ids:
        db.admins.delete_many({"_id": {"$in": ids}})
        db.admin_trusted_devices.delete_many({"adminId": {"$in": ids}})
        db.admin_email_otps.delete_many({"_id": {"$in": ids}})


@pytest.fixture(scope="module", autouse=True)
def _reset_state():
    _wipe_master_2fa()
    _cleanup_test_admins()
    yield
    # teardown: fully disable 2FA on master + clear all trust/otp rows
    _wipe_master_2fa()
    _cleanup_test_admins()


@pytest.fixture(scope="module")
def enrolled_master():
    """Enroll master in TOTP-2FA once and return {token, secret, backup_codes, admin_id}."""
    _wipe_master_2fa()
    r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
    assert r.status_code == 200, r.text
    setup_token = r.json()["setupToken"]
    r = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"})
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    time.sleep(1)
    code = pyotp.TOTP(secret).now()
    r = requests.post(
        f"{API}/admin/2fa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    admin_id = _mongo().admins.find_one({"username": "master"})["_id"]
    return {
        "token": payload["token"],
        "secret": secret,
        "backup_codes": payload["backupCodes"],
        "admin_id": admin_id,
    }


def _get_challenge_token() -> str:
    r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "needs_2fa", d
    return d["twoFactorToken"]


# --- Tests --- #


class TestLoginResponseShape:
    def test_login_includes_available_methods_and_email_hint(self, enrolled_master):
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "needs_2fa"
        assert "twoFactorToken" in d
        assert set(d["availableMethods"]) == {"totp", "email"}
        # obfuscated e.g. h***o@essentialgemstones.com
        assert d["emailHint"].endswith("@essentialgemstones.com")
        assert "*" in d["emailHint"]


class TestMethodsEndpoint:
    def test_get_methods(self, enrolled_master):
        ch = _get_challenge_token()
        r = requests.get(f"{API}/admin/2fa/methods", headers={"Authorization": f"Bearer {ch}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(d["methods"]) == {"totp", "email"}
        assert d["emailHint"].endswith("@essentialgemstones.com")
        assert d["hasBackupCodes"] is True


class TestEmailOtpSend:
    def test_email_send_success_and_row_present(self, enrolled_master):
        # ensure prev row absent for rate limit
        _mongo().admin_email_otps.delete_many({"_id": enrolled_master["admin_id"]})
        ch = _get_challenge_token()
        r = requests.post(f"{API}/admin/2fa/email/send", headers={"Authorization": f"Bearer {ch}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["expiresInMinutes"] == 10
        assert d["resendAfterSeconds"] == 30
        assert d["sentTo"].endswith("@essentialgemstones.com")
        # Row inserted
        row = _mongo().admin_email_otps.find_one({"_id": enrolled_master["admin_id"]})
        assert row is not None
        assert "code_hash" in row
        assert row.get("attempts", 0) == 0
        assert row.get("expires_at")

    def test_email_send_rate_limit_within_30s(self, enrolled_master):
        # ensure a row was recently created (from previous test)
        row = _mongo().admin_email_otps.find_one({"_id": enrolled_master["admin_id"]})
        assert row is not None, "previous test should have left a row"
        ch = _get_challenge_token()
        r = requests.post(f"{API}/admin/2fa/email/send", headers={"Authorization": f"Bearer {ch}"})
        assert r.status_code == 429, r.text
        assert "wait" in r.json()["detail"].lower()


class TestEmailOtpLogin:
    def test_email_otp_success_with_injected_known_code(self, enrolled_master):
        # Directly seed a KNOWN OTP row (bypasses SMTP so we can test consume).
        db = _mongo()
        db.admin_email_otps.update_one(
            {"_id": enrolled_master["admin_id"]},
            {
                "$set": {
                    "code_hash": _hash_password("123456"),
                    "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
                    "sent_at": datetime.utcnow().isoformat(),
                    "attempts": 0,
                }
            },
            upsert=True,
        )
        ch = _get_challenge_token()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": "123456", "method": "email"},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert isinstance(d["token"], str) and len(d["token"]) > 20
        # OTP consumed
        assert db.admin_email_otps.find_one({"_id": enrolled_master["admin_id"]}) is None
        # Full token should work on /admin/me
        r2 = requests.get(f"{API}/admin/me", headers={"Authorization": f"Bearer {d['token']}"})
        assert r2.status_code == 200

    def test_email_otp_wrong_code_returns_401_and_5_attempts_burns_row(self, enrolled_master):
        db = _mongo()
        db.admin_email_otps.update_one(
            {"_id": enrolled_master["admin_id"]},
            {
                "$set": {
                    "code_hash": _hash_password("654321"),
                    "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
                    "sent_at": datetime.utcnow().isoformat(),
                    "attempts": 0,
                }
            },
            upsert=True,
        )
        # 5 wrong attempts, one at a time, each with a fresh challenge token
        for i in range(5):
            ch = _get_challenge_token()
            r = requests.post(
                f"{API}/admin/2fa/login",
                json={"code": "000000", "method": "email"},
                headers={"Authorization": f"Bearer {ch}"},
            )
            assert r.status_code == 401, f"attempt {i+1}: {r.text}"
        # 6th attempt: row was deleted after 5th wrong attempt -> still 401
        ch = _get_challenge_token()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": "654321", "method": "email"},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 401
        # Row purged
        assert db.admin_email_otps.find_one({"_id": enrolled_master["admin_id"]}) is None


class TestTotpMethodAndTrustDevice:
    def test_totp_method_success(self, enrolled_master):
        ch = _get_challenge_token()
        code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code, "method": "totp"},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert "trustDeviceToken" not in d

    def test_totp_with_trust_device_returns_token_and_days(self, enrolled_master):
        # Wait 30s if needed to get a new TOTP code (avoid replay)
        time.sleep(1)
        ch = _get_challenge_token()
        code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code, "method": "totp", "trustDevice": True},
            headers={"Authorization": f"Bearer {ch}", "User-Agent": "pytest-agent/1.0"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert isinstance(d.get("trustDeviceToken"), str) and len(d["trustDeviceToken"]) > 20
        assert d["trustDeviceDays"] == 30
        # Stash for later tests
        pytest.trust_token = d["trustDeviceToken"]
        pytest.full_admin_token = d["token"]

    def test_login_with_trust_token_skips_2fa(self, enrolled_master):
        trust = getattr(pytest, "trust_token", None)
        assert trust, "prior test should have set trust_token"
        r = requests.post(
            f"{API}/admin/login",
            json={"username": MASTER_USER, "password": MASTER_PW},
            headers={"X-Admin-Trust-Token": trust},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "ok"
        assert d["trustedDevice"] is True
        assert isinstance(d["token"], str)
        # verify token
        r2 = requests.get(f"{API}/admin/me", headers={"Authorization": f"Bearer {d['token']}"})
        assert r2.status_code == 200


class TestTrustedDeviceManagement:
    def test_list_trusted_devices_after_trust(self, enrolled_master):
        full = getattr(pytest, "full_admin_token", None)
        assert full, "prior test should have set full_admin_token"
        r = requests.get(f"{API}/admin/trusted-devices", headers={"Authorization": f"Bearer {full}"})
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 1
        row = rows[0]
        for key in ["id", "userAgent", "createdAt", "lastUsedAt", "expiresAt"]:
            assert key in row
        assert row["userAgent"] == "pytest-agent/1.0" or "pytest-agent" in (row["userAgent"] or "")
        pytest.trusted_device_id = row["id"]

    def test_delete_specific_trusted_device_stops_bypass(self, enrolled_master):
        full = pytest.full_admin_token
        trust = pytest.trust_token
        device_id = pytest.trusted_device_id
        # Delete just that device
        r = requests.delete(
            f"{API}/admin/trusted-devices/{device_id}",
            headers={"Authorization": f"Bearer {full}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        # Now login with the same trust token must NOT skip 2FA
        r2 = requests.post(
            f"{API}/admin/login",
            json={"username": MASTER_USER, "password": MASTER_PW},
            headers={"X-Admin-Trust-Token": trust},
        )
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["status"] == "needs_2fa"
        assert "twoFactorToken" in d

    def test_delete_all_trusted_devices(self, enrolled_master):
        # Create two trusted devices first
        for ua in ["ua-A", "ua-B"]:
            time.sleep(1)
            ch = _get_challenge_token()
            code = pyotp.TOTP(enrolled_master["secret"]).now()
            r = requests.post(
                f"{API}/admin/2fa/login",
                json={"code": code, "method": "totp", "trustDevice": True},
                headers={"Authorization": f"Bearer {ch}", "User-Agent": ua},
            )
            assert r.status_code == 200, r.text
            # small wait to force a new totp window not required; different ua ok
        full = pytest.full_admin_token
        # Confirm >=2 devices exist
        r = requests.get(f"{API}/admin/trusted-devices", headers={"Authorization": f"Bearer {full}"})
        assert r.status_code == 200
        count_before = len(r.json())
        assert count_before >= 2
        # Delete all
        r = requests.delete(f"{API}/admin/trusted-devices", headers={"Authorization": f"Bearer {full}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["revoked"] == count_before
        # List → empty
        r = requests.get(f"{API}/admin/trusted-devices", headers={"Authorization": f"Bearer {full}"})
        assert r.status_code == 200
        assert r.json() == []


class TestAutoDetectFallback:
    def test_no_method_totp_still_works(self, enrolled_master):
        time.sleep(1)
        ch = _get_challenge_token()
        code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

    def test_no_method_backup_code_still_works(self, enrolled_master):
        codes = list(enrolled_master["backup_codes"])
        assert codes, "backup codes should be available"
        chosen = codes[-1]
        ch = _get_challenge_token()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": chosen},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        enrolled_master["backup_codes"] = codes[:-1]

    def test_method_backup_explicit_still_works(self, enrolled_master):
        codes = list(enrolled_master["backup_codes"])
        assert codes, "backup codes should be available"
        chosen = codes[-1]
        ch = _get_challenge_token()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": chosen, "method": "backup"},
            headers={"Authorization": f"Bearer {ch}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        enrolled_master["backup_codes"] = codes[:-1]


class TestDisableAndResetPurgeSideEffects:
    def _create_temp_super_admin_and_2fa(self):
        """Create a fresh admin, enable 2FA, add a trusted device. Returns dict."""
        # Use master to create
        # First ensure we have a full master token (last used in prior tests may be revoked when we delete all devices? No — full token is separate JWT)
        db = _mongo()
        # Login master + TOTP to get a fresh full token
        time.sleep(1)
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r.status_code == 200, r.text
        two_fa = r.json()["twoFactorToken"]
        master_secret = getattr(pytest, "master_secret", None)
        # We can't rely on pytest attr—read from enrolled_master fixture through class fixture is nicer, but we
        # keep it local: fetch via _mongo? No—secret is not stored plaintext accessible; use module-level fixture.
        # This helper is only called from a test that has access to `enrolled_master` fixture.
        return two_fa

    def test_disable_2fa_purges_trusted_devices(self, enrolled_master):
        # First create a trusted device so we can verify it disappears
        time.sleep(1)
        ch = _get_challenge_token()
        code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code, "method": "totp", "trustDevice": True},
            headers={"Authorization": f"Bearer {ch}", "User-Agent": "purge-test"},
        )
        assert r.status_code == 200, r.text
        full = r.json()["token"]
        trust = r.json()["trustDeviceToken"]

        # confirm device exists
        db = _mongo()
        assert db.admin_trusted_devices.count_documents({"adminId": enrolled_master["admin_id"]}) >= 1

        # Disable 2FA with valid TOTP
        time.sleep(1)
        disable_code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/disable",
            json={"code": disable_code},
            headers={"Authorization": f"Bearer {full}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # Verify all trusted devices for this admin are gone
        assert db.admin_trusted_devices.count_documents({"adminId": enrolled_master["admin_id"]}) == 0
        # Verify email OTP row is gone too
        assert db.admin_email_otps.count_documents({"_id": enrolled_master["admin_id"]}) == 0

        # And re-enroll master so subsequent tests still work
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r.status_code == 200
        assert r.json()["status"] == "needs_2fa_setup"
        setup_token = r.json()["setupToken"]
        r = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"})
        assert r.status_code == 200
        new_secret = r.json()["secret"]
        time.sleep(1)
        r = requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": pyotp.TOTP(new_secret).now()},
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert r.status_code == 200
        enrolled_master["secret"] = new_secret
        enrolled_master["token"] = r.json()["token"]
        enrolled_master["backup_codes"] = r.json()["backupCodes"]

    def test_super_reset_purges_trusted_devices_and_email_otps(self, enrolled_master):
        db = _mongo()
        # Create a target admin
        uname = f"test_reset_{uuid.uuid4().hex[:6]}"
        c = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW, "isSuper": False, "email": f"{uname}@example.com"},
            headers={"Authorization": f"Bearer {enrolled_master['token']}"},
        )
        assert c.status_code == 200, c.text
        target_id = c.json()["id"]

        # Enroll target in 2FA
        r = requests.post(f"{API}/admin/login", json={"username": uname, "password": STRONG_PW})
        assert r.status_code == 200
        setup_token = r.json()["setupToken"]
        secret = requests.post(
            f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"}
        ).json()["secret"]
        time.sleep(1)
        r = requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": pyotp.TOTP(secret).now()},
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert r.status_code == 200
        target_full = r.json()["token"]

        # Trust a device
        time.sleep(1)
        r = requests.post(f"{API}/admin/login", json={"username": uname, "password": STRONG_PW})
        assert r.status_code == 200
        two_fa_ch = r.json()["twoFactorToken"]
        code = pyotp.TOTP(secret).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code, "method": "totp", "trustDevice": True},
            headers={"Authorization": f"Bearer {two_fa_ch}", "User-Agent": "reset-target"},
        )
        assert r.status_code == 200, r.text

        # Add a fake email OTP row
        db.admin_email_otps.update_one(
            {"_id": target_id},
            {
                "$set": {
                    "code_hash": _hash_password("111111"),
                    "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
                    "sent_at": datetime.utcnow().isoformat(),
                    "attempts": 0,
                }
            },
            upsert=True,
        )
        assert db.admin_trusted_devices.count_documents({"adminId": target_id}) >= 1
        assert db.admin_email_otps.count_documents({"_id": target_id}) == 1

        # Super (master) resets target's 2FA
        r = requests.post(
            f"{API}/admin/2fa/reset/{target_id}",
            headers={"Authorization": f"Bearer {enrolled_master['token']}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # Verify purges
        assert db.admin_trusted_devices.count_documents({"adminId": target_id}) == 0
        assert db.admin_email_otps.count_documents({"_id": target_id}) == 0

        # Cleanup
        db.admins.delete_one({"_id": target_id})


class TestRegressionSetupEnableRegenerate:
    """Quick smoke that pre-existing 2FA flows still work end-to-end."""

    def test_backup_code_regeneration_still_works(self, enrolled_master):
        time.sleep(1)
        code = pyotp.TOTP(enrolled_master["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/backup-codes/regenerate",
            json={"code": code},
            headers={"Authorization": f"Bearer {enrolled_master['token']}"},
        )
        assert r.status_code == 200, r.text
        codes = r.json()["backupCodes"]
        assert isinstance(codes, list) and len(codes) == 10
