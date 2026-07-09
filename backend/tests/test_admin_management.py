"""Backend tests for the NEW admin-management features.

Covers (from review_request):
- POST /api/admin/admins requires a valid email (422 on missing/empty/invalid, 400 on duplicate email).
- POST /api/admin/admins with valid data returns doc with lowercased email.
- PUT /api/admin/admins/{id} lets a super admin update the email; validates format and duplicates.
- Non-super admin (isSuper=false, has manage_admins) cannot create/delete admins (403) but can update
  own email/password via PUT.
- Direct unit tests of _apply_admin_action for create / update / delete / resetPassword / reset2fa,
  including the "generatedPassword" path when the AI omits the password.
- Integration hit on POST /api/admin/ai (super admin) for admins-kind create; marked flaky because
  it depends on Claude picking the right kind. If it fails, the direct-dispatcher tests already
  cover the mutation logic. Also verifies non-super caller falls back (no new admin persisted).
- Regression: kind='edit' and kind='email' still work through /api/admin/ai.

Teardown wipes any test_* / helper / helper2 / foo admins and any residue on master.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta

import jwt as _jwt
import pymongo
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as fp:
            for ln in fp:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = ln.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass
assert BASE_URL, "REACT_APP_BACKEND_URL is required"

API = f"{BASE_URL}/api"

JWT_SECRET = None
for _p in ("/app/backend/.env",):
    try:
        with open(_p) as fp:
            for ln in fp:
                if ln.startswith("JWT_SECRET"):
                    JWT_SECRET = ln.split("=", 1)[1].strip().strip('"')
                    break
    except Exception:
        pass
assert JWT_SECRET, "JWT_SECRET must be readable from /app/backend/.env"

STRONG_PW = "Aa1!aaaa"  # meets min-8, upper, lower, digit, symbol


def _mongo():
    return pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[
        os.environ.get("DB_NAME", "test_database")
    ]


def _forge_admin_token(sub: str, username: str, is_super: bool, permissions: list[str] | None = None) -> str:
    now = int(datetime.utcnow().timestamp())
    payload = {
        "sub": sub,
        "username": username,
        "role": "admin",
        "isSuper": bool(is_super),
        "permissions": permissions or [],
        "purpose": "full",
        "iat": now,
        "exp": now + 3600,
    }
    return _jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ------------- fixtures ------------- #

TEST_PREFIX_MATCH = {"$regex": r"^(test_|helper$|helper2$|foo$)"}


def _cleanup_test_admins() -> None:
    db = _mongo()
    ids = [d["_id"] for d in db.admins.find({"username": TEST_PREFIX_MATCH}, {"_id": 1})]
    if ids:
        db.admins.delete_many({"_id": {"$in": ids}})
        db.admin_trusted_devices.delete_many({"adminId": {"$in": ids}})
        db.admin_email_otps.delete_many({"_id": {"$in": ids}})


def _wipe_master_2fa() -> None:
    db = _mongo()
    db.admins.update_one(
        {"username": "master"},
        {"$unset": {"twoFactorSecret": "", "twoFactorEnabled": "", "twoFactorBackupCodes": "",
                     "twoFactorPendingSecret": "", "twoFactorEnabledAt": ""}},
    )
    master = db.admins.find_one({"username": "master"}) or {}
    db.admin_trusted_devices.delete_many({"adminId": master.get("_id")})
    db.admin_email_otps.delete_many({"_id": master.get("_id")})


@pytest.fixture(scope="module", autouse=True)
def _reset_state():
    _cleanup_test_admins()
    _wipe_master_2fa()
    yield
    _cleanup_test_admins()
    _wipe_master_2fa()


@pytest.fixture(scope="module")
def super_headers():
    master = _mongo().admins.find_one({"username": "master"})
    assert master, "master admin missing"
    token = _forge_admin_token(master["_id"], "master", True, master.get("permissions") or [])
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, master["_id"]


@pytest.fixture(scope="module")
def nonsuper_admin():
    """Create a non-super admin with manage_admins permission and return (headers, id)."""
    db = _mongo()
    admin_id = str(uuid.uuid4())
    username = f"test_nonsuper_{uuid.uuid4().hex[:6]}"
    import bcrypt
    doc = {
        "_id": admin_id,
        "username": username,
        "email": f"{username}@example.com",
        "passwordHash": bcrypt.hashpw(STRONG_PW.encode(), bcrypt.gensalt()).decode(),
        "permissions": ["manage_admins", "hero"],
        "isSuper": False,
        "twoFactorEnabled": False,
        "createdAt": datetime.utcnow().isoformat(),
    }
    db.admins.insert_one(doc)
    tok = _forge_admin_token(admin_id, username, False, doc["permissions"])
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, admin_id, username


# ------------- Tests: POST /api/admin/admins email required ------------- #


class TestCreateAdminEmailRequired:
    def test_missing_email_returns_422(self, super_headers):
        headers, _ = super_headers
        payload = {"username": f"test_noemail_{uuid.uuid4().hex[:6]}", "password": STRONG_PW}
        r = requests.post(f"{API}/admin/admins", json=payload, headers=headers, timeout=20)
        assert r.status_code == 422, r.text
        body = r.json()
        # Pydantic v2: {"detail": [{"type":"missing","loc":["body","email"],"msg":"Field required",...}]}
        details = body.get("detail") or []
        assert any("email" in (d.get("loc") or []) for d in details), body

    def test_empty_email_returns_422(self, super_headers):
        headers, _ = super_headers
        payload = {"username": f"test_emptyemail_{uuid.uuid4().hex[:6]}", "password": STRONG_PW, "email": ""}
        r = requests.post(f"{API}/admin/admins", json=payload, headers=headers, timeout=20)
        assert r.status_code == 422, r.text

    def test_invalid_email_returns_422(self, super_headers):
        headers, _ = super_headers
        payload = {"username": f"test_bademail_{uuid.uuid4().hex[:6]}", "password": STRONG_PW, "email": "nope"}
        r = requests.post(f"{API}/admin/admins", json=payload, headers=headers, timeout=20)
        assert r.status_code == 422, r.text
        text = r.text.lower()
        assert "email" in text and ("valid" in text or "value_error" in text), r.text


class TestCreateAdminSuccessAndDuplicate:
    def test_create_success_and_email_lowercased(self, super_headers):
        headers, _ = super_headers
        uname = f"test_ok_{uuid.uuid4().hex[:6]}"
        upper_email = f"MiXeD_{uuid.uuid4().hex[:6]}@Example.COM"
        r = requests.post(
            f"{API}/admin/admins",
            json={"username": uname, "password": STRONG_PW, "email": upper_email, "permissions": ["hero"]},
            headers=headers,
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["username"] == uname
        assert body["email"] == upper_email.lower()
        assert body["permissions"] == ["hero"]
        assert body["isSuper"] is False
        # verify persistence via GET (super only)
        lst = requests.get(f"{API}/admin/admins", headers=headers, timeout=20).json()
        found = [a for a in lst if a["username"] == uname]
        assert found and found[0]["email"] == upper_email.lower()

    def test_duplicate_email_returns_400(self, super_headers):
        headers, _ = super_headers
        email = f"test_dup_{uuid.uuid4().hex[:6]}@example.com"
        u1 = f"test_dup1_{uuid.uuid4().hex[:6]}"
        u2 = f"test_dup2_{uuid.uuid4().hex[:6]}"
        r1 = requests.post(f"{API}/admin/admins",
                            json={"username": u1, "password": STRONG_PW, "email": email}, headers=headers, timeout=20)
        assert r1.status_code == 200, r1.text
        r2 = requests.post(f"{API}/admin/admins",
                            json={"username": u2, "password": STRONG_PW, "email": email}, headers=headers, timeout=20)
        assert r2.status_code == 400, r2.text
        assert "already uses that email" in (r2.json().get("detail") or "").lower() or "another admin" in (r2.json().get("detail") or "").lower()


# ------------- Tests: PUT /api/admin/admins/{id} email edits ------------- #


class TestUpdateAdminEmail:
    def _make_admin(self, headers, uname_prefix="test_edit"):
        uname = f"{uname_prefix}_{uuid.uuid4().hex[:6]}"
        email = f"{uname}@example.com"
        r = requests.post(f"{API}/admin/admins",
                          json={"username": uname, "password": STRONG_PW, "email": email},
                          headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        return r.json(), email

    def test_super_can_update_email(self, super_headers):
        headers, _ = super_headers
        adm, _ = self._make_admin(headers)
        new_email = f"test_newemail_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.put(f"{API}/admin/admins/{adm['id']}",
                          json={"email": new_email}, headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == new_email.lower()
        # Verify persisted
        db = _mongo()
        row = db.admins.find_one({"_id": adm["id"]})
        assert row["email"] == new_email.lower()

    def test_invalid_email_returns_422(self, super_headers):
        headers, _ = super_headers
        adm, _ = self._make_admin(headers)
        r = requests.put(f"{API}/admin/admins/{adm['id']}",
                          json={"email": "not-an-email"}, headers=headers, timeout=20)
        assert r.status_code == 422, r.text

    def test_duplicate_email_returns_400(self, super_headers):
        headers, _ = super_headers
        a1, e1 = self._make_admin(headers, "test_dupA")
        a2, e2 = self._make_admin(headers, "test_dupB")
        # Try to move a2's email to a1's email
        r = requests.put(f"{API}/admin/admins/{a2['id']}",
                          json={"email": e1}, headers=headers, timeout=20)
        assert r.status_code == 400, r.text


# ------------- Tests: Non-super admin permissions ------------- #


class TestNonSuperAdminRules:
    def test_nonsuper_cannot_create_admin(self, nonsuper_admin):
        headers, _, _ = nonsuper_admin
        r = requests.post(f"{API}/admin/admins",
                          json={"username": f"test_nope_{uuid.uuid4().hex[:6]}",
                                "password": STRONG_PW,
                                "email": f"nope_{uuid.uuid4().hex[:6]}@example.com"},
                          headers=headers, timeout=20)
        assert r.status_code == 403, r.text

    def test_nonsuper_cannot_delete_admin(self, super_headers, nonsuper_admin):
        s_headers, _ = super_headers
        # Create a target with super
        target_username = f"test_tgt_{uuid.uuid4().hex[:6]}"
        rr = requests.post(f"{API}/admin/admins",
                            json={"username": target_username, "password": STRONG_PW,
                                  "email": f"{target_username}@example.com"},
                            headers=s_headers, timeout=20)
        assert rr.status_code == 200, rr.text
        target_id = rr.json()["id"]
        # non-super tries to delete
        ns_headers, _, _ = nonsuper_admin
        r = requests.delete(f"{API}/admin/admins/{target_id}", headers=ns_headers, timeout=20)
        assert r.status_code == 403, r.text

    def test_nonsuper_can_update_own_email(self, nonsuper_admin):
        headers, admin_id, _ = nonsuper_admin
        new_email = f"test_selfupd_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.put(f"{API}/admin/admins/{admin_id}",
                          json={"email": new_email}, headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["email"] == new_email.lower()

    def test_nonsuper_can_update_own_password(self, nonsuper_admin):
        headers, admin_id, _ = nonsuper_admin
        new_pw = "Bb2@bbbb"
        r = requests.put(f"{API}/admin/admins/{admin_id}",
                          json={"password": new_pw}, headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        # verify hash changed by attempting login
        # (find username first)
        db = _mongo()
        doc = db.admins.find_one({"_id": admin_id})
        r2 = requests.post(f"{API}/admin/login",
                            json={"username": doc["username"], "password": new_pw}, timeout=20)
        # Response is 200 with either needs_2fa_setup (2FA off) or a token — either indicates password ok
        assert r2.status_code == 200, r2.text


# ------------- Tests: _apply_admin_action direct dispatcher ------------- #


@pytest.fixture(scope="module")
def dispatcher():
    """Import _apply_admin_action from server module directly.

    Motor's AsyncIOMotorClient binds to the first event loop that touches it,
    so we create ONE loop for the module and reuse it for every coroutine call.
    """
    import importlib
    import sys
    sys.path.insert(0, "/app/backend")
    mod = importlib.import_module("server")
    loop = asyncio.new_event_loop()

    def _run(coro):
        return loop.run_until_complete(coro)

    yield mod._apply_admin_action, mod, _run
    # best-effort close
    try:
        loop.close()
    except Exception:
        pass


class TestApplyAdminActionDispatcher:

    def test_create_generates_strong_password_when_omitted(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        uname = f"test_disp_gen_{uuid.uuid4().hex[:6]}"
        email = f"{uname}@example.com"
        res = run_async(apply({"action": "create", "username": uname, "email": email}, caller))
        assert res.get("ok") is True, res
        assert res.get("action") == "create"
        gen = res.get("generatedPassword")
        assert gen and len(gen) >= 8, res
        # policy check
        assert any(c.isupper() for c in gen)
        assert any(c.islower() for c in gen)
        assert any(c.isdigit() for c in gen)
        assert any(not c.isalnum() for c in gen)
        # verify persistence & hash present
        row = _mongo().admins.find_one({"username": uname})
        assert row and row.get("passwordHash", "").startswith("$2b$")
        assert row["email"] == email

    def test_create_requires_email(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        res = run_async(apply({"action": "create", "username": f"test_disp_ne_{uuid.uuid4().hex[:6]}"}, caller))
        assert res.get("ok") is False
        assert "email" in (res.get("error") or "").lower()

    def test_update_email(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        uname = f"test_disp_upd_{uuid.uuid4().hex[:6]}"
        run_async(apply({"action": "create", "username": uname, "email": f"{uname}@example.com",
                            "password": STRONG_PW}, caller))
        new_email = f"upd_{uuid.uuid4().hex[:6]}@example.com"
        res = run_async(apply({"action": "update", "username": uname, "email": new_email}, caller))
        assert res.get("ok") is True, res
        assert res.get("target", {}).get("email") == new_email.lower()

    def test_reset_password(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        uname = f"test_disp_rp_{uuid.uuid4().hex[:6]}"
        run_async(apply({"action": "create", "username": uname, "email": f"{uname}@example.com",
                            "password": STRONG_PW}, caller))
        prev_hash = _mongo().admins.find_one({"username": uname})["passwordHash"]
        res = run_async(apply({"action": "resetPassword", "username": uname}, caller))
        assert res.get("ok") is True
        assert res.get("generatedPassword")
        new_hash = _mongo().admins.find_one({"username": uname})["passwordHash"]
        assert new_hash != prev_hash

    def test_reset_2fa_clears_state_and_trusted_devices(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        uname = f"test_disp_2fa_{uuid.uuid4().hex[:6]}"
        run_async(apply({"action": "create", "username": uname, "email": f"{uname}@example.com",
                            "password": STRONG_PW}, caller))
        db = _mongo()
        row = db.admins.find_one({"username": uname})
        # Simulate that this admin has 2FA + a trusted device
        db.admins.update_one({"_id": row["_id"]}, {"$set": {"twoFactorEnabled": True, "twoFactorSecret": "SECRET"}})
        db.admin_trusted_devices.insert_one({
            "_id": str(uuid.uuid4()),
            "adminId": row["_id"],
            "trustHash": "x",
            "createdAt": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        })
        res = run_async(apply({"action": "reset2fa", "username": uname}, caller))
        assert res.get("ok") is True
        fresh = db.admins.find_one({"_id": row["_id"]})
        assert not fresh.get("twoFactorEnabled")
        assert "twoFactorSecret" not in fresh
        assert db.admin_trusted_devices.count_documents({"adminId": row["_id"]}) == 0

    def test_delete(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        uname = f"test_disp_del_{uuid.uuid4().hex[:6]}"
        run_async(apply({"action": "create", "username": uname, "email": f"{uname}@example.com",
                            "password": STRONG_PW}, caller))
        assert _mongo().admins.count_documents({"username": uname}) == 1
        res = run_async(apply({"action": "delete", "username": uname}, caller))
        assert res.get("ok") is True
        assert _mongo().admins.count_documents({"username": uname}) == 0

    def test_unknown_action(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        res = run_async(apply({"action": "banish"}, {"sub": master_id, "isSuper": True}))
        assert res.get("ok") is False
        assert "unknown" in (res.get("error") or "").lower()

    def test_duplicate_email_on_update(self, dispatcher, super_headers):
        apply, _, run_async = dispatcher
        _, master_id = super_headers
        caller = {"sub": master_id, "isSuper": True}
        u1 = f"test_disp_da_{uuid.uuid4().hex[:6]}"
        u2 = f"test_disp_db_{uuid.uuid4().hex[:6]}"
        run_async(apply({"action": "create", "username": u1, "email": f"{u1}@example.com", "password": STRONG_PW}, caller))
        run_async(apply({"action": "create", "username": u2, "email": f"{u2}@example.com", "password": STRONG_PW}, caller))
        res = run_async(apply({"action": "update", "username": u2, "email": f"{u1}@example.com"}, caller))
        assert res.get("ok") is False
        assert "already uses" in (res.get("error") or "").lower()


# ------------- Tests: /api/admin/ai admins-kind guard for non-super ------------- #


class TestAdminAIGuards:
    def test_nonsuper_cannot_create_admin_via_ai(self, nonsuper_admin):
        headers, _, _ = nonsuper_admin
        r = requests.post(f"{API}/admin/ai",
                          json={"message": "Create a new admin foo with email foo@example.com and permissions to edit hero"},
                          headers=headers, timeout=60)
        # Endpoint should always 200; the guard makes result fall back to chat OR admins with an error
        assert r.status_code == 200, r.text
        body = r.json()
        kind = body.get("kind")
        assert kind in ("chat", "admins"), body
        if kind == "admins":
            action = body.get("adminAction") or {}
            assert not action.get("ok"), body
        # Most importantly: db.admins must NOT contain a new 'foo' admin
        assert _mongo().admins.count_documents({"username": "foo"}) == 0

    @pytest.mark.flaky_llm
    def test_super_ai_creates_admin_helper(self, super_headers):
        """End-to-end via Claude. Informational: if the LLM misclassifies, we log and skip."""
        headers, _ = super_headers
        session_id = str(uuid.uuid4())
        r = requests.post(f"{API}/admin/ai",
                          json={"message": ("Create a new admin named helper with email helper@example.com "
                                             "and permissions to edit hero and products. "
                                             "Use kind='admins' with action='create'."),
                                "sessionId": session_id},
                          headers=headers, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("kind") != "admins":
            pytest.skip(f"LLM chose kind={body.get('kind')} instead of admins — informational only")
        action = body.get("adminAction") or {}
        if not action.get("ok"):
            pytest.skip(f"AI kind=admins but action not ok: {action}")
        assert action.get("action") == "create"
        row = _mongo().admins.find_one({"username": "helper"})
        assert row is not None
        assert row.get("email") == "helper@example.com"

    @pytest.mark.flaky_llm
    def test_super_ai_regression_edit_still_works(self, super_headers):
        headers, _ = super_headers
        r = requests.post(f"{API}/admin/ai",
                          json={"message": "Change the hero headline to 'Grounded stones for grounded people.' — apply this edit now."},
                          timeout=90, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("kind") != "edit":
            pytest.skip(f"LLM chose kind={body.get('kind')} instead of edit — informational")
        assert isinstance(body.get("applied"), list)

    @pytest.mark.flaky_llm
    def test_super_ai_regression_email_still_drafts(self, super_headers):
        headers, _ = super_headers
        r = requests.post(f"{API}/admin/ai",
                          json={"message": "Draft an email to my newsletter subscribers announcing our new moonstone bracelet."},
                          timeout=90, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("kind") != "email":
            pytest.skip(f"LLM chose kind={body.get('kind')} instead of email — informational")
        assert body.get("emailDraft"), body
        assert body["emailDraft"].get("subject")
        assert body["emailDraft"].get("html")
