"""Backend tests for admin 2FA (TOTP), backup codes, password policy, and full-session JWT.

Covers:
- Legacy master-password shortcut removed
- Master admin auto-seeded
- Login → needs_2fa_setup → /2fa/setup → /2fa/enable → backup codes
- Second login → needs_2fa → /2fa/login (TOTP or backup code)
- Password policy enforcement on admin/{create,update} and /auth/register
- 2FA reset (super) and 2FA disable (self)
- Full-session JWT works on all admin routes; setup/challenge tokens rejected
"""
import os
import re
import time
import uuid

import pymongo
import pyotp
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gemstone-makeover.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MASTER_USER = "master"
MASTER_PW = "1121211221"          # legacy grandfathered password
STRONG_PW = "Aa1!aaaa"             # meets policy
WEAK_PW = "weak"


# ---------- helpers ----------

def _mongo():
    return pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]


def _wipe_master_2fa():
    """Reset master admin to no-2FA state so tests are deterministic."""
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


def _cleanup_test_admins():
    db = _mongo()
    db.admins.delete_many({"username": {"$regex": "^test_"}})


@pytest.fixture(scope="module", autouse=True)
def _reset_state():
    _wipe_master_2fa()
    _cleanup_test_admins()
    yield
    _wipe_master_2fa()
    _cleanup_test_admins()


@pytest.fixture(scope="module")
def full_admin_token():
    """Enroll master 2FA once and return a full-session JWT. Also stashes secret."""
    _wipe_master_2fa()
    # Step 1: login → needs_2fa_setup
    r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "needs_2fa_setup"
    setup_token = data["setupToken"]

    # Step 2: /admin/2fa/setup
    r = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"})
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]

    # Step 3: /admin/2fa/enable
    code = pyotp.TOTP(secret).now()
    r = requests.post(
        f"{API}/admin/2fa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {setup_token}"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["ok"] is True
    return {
        "token": payload["token"],
        "secret": secret,
        "backup_codes": payload["backupCodes"],
        "user": payload["user"],
    }


# ---------- Tests: legacy shortcut removed & master admin ----------

class TestLegacyShortcut:
    def test_login_password_only_returns_400(self):
        r = requests.post(f"{API}/admin/login", json={"password": MASTER_PW})
        assert r.status_code == 400
        assert "required" in r.json()["detail"].lower()

    def test_login_username_only_returns_400(self):
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": ""})
        assert r.status_code == 400

    def test_login_wrong_password_returns_401(self):
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": "nope"})
        assert r.status_code == 401


class TestMasterSeed:
    def test_master_exists(self):
        db = _mongo()
        m = db.admins.find_one({"username": "master"})
        assert m is not None
        assert m.get("isSuper") is True


# ---------- Tests: 2FA enrollment flow ----------

class TestTwoFactorEnrollment:
    def test_login_returns_needs_2fa_setup(self):
        _wipe_master_2fa()
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "needs_2fa_setup"
        assert "setupToken" in data and isinstance(data["setupToken"], str) and len(data["setupToken"]) > 20
        assert data["user"]["username"] == "master"

    def test_setup_token_cannot_hit_real_admin_routes(self):
        _wipe_master_2fa()
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        setup_token = r.json()["setupToken"]
        # Attempt PUT /api/site with setup token
        r2 = requests.put(
            f"{API}/site",
            json={"hero": {"kicker": "should not apply"}},
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert r2.status_code == 401
        assert "2fa" in r2.json()["detail"].lower() or "setup" in r2.json()["detail"].lower()

    def test_2fa_setup_returns_qr_and_uri(self):
        _wipe_master_2fa()
        setup_token = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["setupToken"]
        r = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"})
        assert r.status_code == 200
        d = r.json()
        assert re.fullmatch(r"[A-Z2-7]+", d["secret"])
        assert d["qrDataUrl"].startswith("data:image/png;base64,")
        assert d["provisioningUri"].startswith("otpauth://")
        assert d["digits"] == 6
        assert d["period"] == 30
        assert d["algorithm"] == "SHA1"
        assert d["issuer"]
        assert d["accountName"] == "master"

    def test_2fa_enable_returns_10_backup_codes_and_full_token(self):
        _wipe_master_2fa()
        setup_token = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["setupToken"]
        secret = requests.post(
            f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"}
        ).json()["secret"]
        code = pyotp.TOTP(secret).now()
        r = requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": code},
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["user"]["twoFactorEnabled"] is True
        assert "token" in d and isinstance(d["token"], str)
        codes = d["backupCodes"]
        assert isinstance(codes, list) and len(codes) == 10
        for c in codes:
            assert re.fullmatch(r"[A-F0-9]{4}-[A-F0-9]{4}", c), c


# ---------- Tests: 2FA challenge login ----------

class TestTwoFactorLogin:
    def test_login_after_enroll_returns_needs_2fa(self, full_admin_token):
        r = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "needs_2fa"
        assert "twoFactorToken" in d
        # And ensure that token is NOT a full admin token — reject on /admin/site
        r2 = requests.put(
            f"{API}/site",
            json={"hero": {"kicker": "nope"}},
            headers={"Authorization": f"Bearer {d['twoFactorToken']}"},
        )
        assert r2.status_code == 401

    def test_2fa_login_wrong_code(self, full_admin_token):
        two_fa_token = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["twoFactorToken"]
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {two_fa_token}"},
        )
        assert r.status_code == 401

    def test_2fa_login_correct_code(self, full_admin_token):
        two_fa_token = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["twoFactorToken"]
        code = pyotp.TOTP(full_admin_token["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": code},
            headers={"Authorization": f"Bearer {two_fa_token}"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["token"]
        assert d["user"]["twoFactorEnabled"] is True

    def test_backup_code_works_once(self, full_admin_token):
        # Pick a fresh backup code (grab first one from module fixture)
        codes = list(full_admin_token["backup_codes"])
        # Read current DB list length
        db = _mongo()
        before = len((db.admins.find_one({"username": "master"}) or {}).get("twoFactorBackupCodes") or [])
        # Get challenge token
        two_fa_token = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["twoFactorToken"]
        # Use the LAST backup code we haven't consumed
        chosen = codes[-1]
        r = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": chosen},
            headers={"Authorization": f"Bearer {two_fa_token}"},
        )
        assert r.status_code == 200, r.text
        # Reuse same code → 401
        two_fa_token_2 = requests.post(
            f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW}
        ).json()["twoFactorToken"]
        r2 = requests.post(
            f"{API}/admin/2fa/login",
            json={"code": chosen},
            headers={"Authorization": f"Bearer {two_fa_token_2}"},
        )
        assert r2.status_code == 401
        # Remove from local copy
        full_admin_token["backup_codes"] = codes[:-1]
        after = len((db.admins.find_one({"username": "master"}) or {}).get("twoFactorBackupCodes") or [])
        assert after == before - 1


# ---------- Tests: password policy ----------

class TestPasswordPolicy:
    def test_admin_create_weak_password_rejected(self, full_admin_token):
        r = requests.post(
            f"{API}/admin/admins",
            json={"username": f"test_weak_{uuid.uuid4().hex[:6]}", "password": WEAK_PW},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 400
        assert "password" in r.json()["detail"].lower()

    def test_admin_create_strong_password_ok(self, full_admin_token):
        uname = f"test_strong_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW, "isSuper": False},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["username"] == uname
        assert d["twoFactorEnabled"] is False

    def test_admin_update_weak_password_rejected(self, full_admin_token):
        # Create then try update with weak
        uname = f"test_upd_{uuid.uuid4().hex[:6]}"
        c = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert c.status_code == 200
        aid = c.json()["id"]
        r = requests.put(
            f"{API}/admin/admins/{aid}",
            json={"password": WEAK_PW},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 400

    def test_register_weak_password_rejected(self):
        r = requests.post(
            f"{API}/auth/register",
            json={
                "fullName": "Test User",
                "email": f"TEST_weak_{uuid.uuid4().hex[:6]}@example.com",
                "password": WEAK_PW,
                "subscribeNewsletter": False,
            },
        )
        assert r.status_code == 400

    def test_register_strong_password_ok(self):
        email = f"TEST_strong_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "fullName": "Test User",
                "email": email,
                "password": STRONG_PW,
                "subscribeNewsletter": False,
            },
        )
        # Might be 200 even if SMTP fails (best-effort emails)
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == email.lower()
        # cleanup
        _mongo().users.delete_one({"email": email.lower()})
        _mongo().subscribers.delete_one({"email": email.lower()})


# ---------- Tests: 2FA reset + disable ----------

class TestTwoFactorAdminActions:
    def test_non_super_cannot_reset_2fa(self, full_admin_token):
        # Create a non-super admin and grab their JWT via enrollment
        uname = f"test_nonsuper_{uuid.uuid4().hex[:6]}"
        c = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW, "isSuper": False, "permissions": ["hero"]},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert c.status_code == 200
        target_id = c.json()["id"]

        # Enroll them
        login = requests.post(f"{API}/admin/login", json={"username": uname, "password": STRONG_PW}).json()
        setup_token = login["setupToken"]
        secret = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"}).json()["secret"]
        enable = requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": pyotp.TOTP(secret).now()},
            headers={"Authorization": f"Bearer {setup_token}"},
        ).json()
        non_super_token = enable["token"]

        # Non-super tries to reset master's 2FA → 403
        db = _mongo()
        master_id = db.admins.find_one({"username": "master"})["_id"]
        r = requests.post(
            f"{API}/admin/2fa/reset/{master_id}",
            headers={"Authorization": f"Bearer {non_super_token}"},
        )
        assert r.status_code == 403

    def test_super_can_reset_2fa(self, full_admin_token):
        # Create a target super-enrolled admin
        uname = f"test_target_{uuid.uuid4().hex[:6]}"
        c = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW, "isSuper": False},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        target_id = c.json()["id"]
        # Enroll
        setup_token = requests.post(f"{API}/admin/login", json={"username": uname, "password": STRONG_PW}).json()["setupToken"]
        secret = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"}).json()["secret"]
        requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": pyotp.TOTP(secret).now()},
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        # Now super resets
        r = requests.post(
            f"{API}/admin/2fa/reset/{target_id}",
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Next login → needs_2fa_setup
        r2 = requests.post(f"{API}/admin/login", json={"username": uname, "password": STRONG_PW})
        assert r2.json()["status"] == "needs_2fa_setup"

    def test_2fa_disable_bad_code_401(self, full_admin_token):
        r = requests.post(
            f"{API}/admin/2fa/disable",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 401

    def test_2fa_disable_good_code_ok_then_reenroll(self, full_admin_token):
        # Use current code
        code = pyotp.TOTP(full_admin_token["secret"]).now()
        r = requests.post(
            f"{API}/admin/2fa/disable",
            json={"code": code},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 200
        # Now login should go back to needs_2fa_setup
        r2 = requests.post(f"{API}/admin/login", json={"username": MASTER_USER, "password": MASTER_PW})
        assert r2.json()["status"] == "needs_2fa_setup"

        # Re-enroll so subsequent tests still have a valid full_admin_token
        setup_token = r2.json()["setupToken"]
        new_secret = requests.post(f"{API}/admin/2fa/setup", headers={"Authorization": f"Bearer {setup_token}"}).json()["secret"]
        enable = requests.post(
            f"{API}/admin/2fa/enable",
            json={"code": pyotp.TOTP(new_secret).now()},
            headers={"Authorization": f"Bearer {setup_token}"},
        ).json()
        full_admin_token["secret"] = new_secret
        full_admin_token["token"] = enable["token"]
        full_admin_token["backup_codes"] = enable["backupCodes"]


# ---------- Tests: full session token works on all admin routes ----------

class TestFullTokenNoRegression:
    def test_get_admins(self, full_admin_token):
        r = requests.get(f"{API}/admin/admins", headers={"Authorization": f"Bearer {full_admin_token['token']}"})
        assert r.status_code == 200
        users = r.json()
        assert any(u["username"] == "master" for u in users)

    def test_put_site(self, full_admin_token):
        r = requests.put(
            f"{API}/site",
            json={"hero": {"kicker": "TEST_2FA_KICKER"}},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r.status_code == 200
        assert r.json()["hero"]["kicker"] == "TEST_2FA_KICKER"

    def test_admin_me(self, full_admin_token):
        r = requests.get(f"{API}/admin/me", headers={"Authorization": f"Bearer {full_admin_token['token']}"})
        assert r.status_code == 200
        assert r.json()["user"]["username"] == "master"

    def test_backup_codes_remaining_and_regenerate(self, full_admin_token):
        r = requests.get(f"{API}/admin/2fa/backup-codes", headers={"Authorization": f"Bearer {full_admin_token['token']}"})
        assert r.status_code == 200
        assert r.json()["enabled"] is True
        code = pyotp.TOTP(full_admin_token["secret"]).now()
        r2 = requests.post(
            f"{API}/admin/2fa/backup-codes/regenerate",
            json={"code": code},
            headers={"Authorization": f"Bearer {full_admin_token['token']}"},
        )
        assert r2.status_code == 200
        codes = r2.json()["backupCodes"]
        assert len(codes) == 10
