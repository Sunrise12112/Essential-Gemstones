"""Auth safeguards + SMS/TOTP regression coverage.

# Modules/features covered: login throttles, CORS, member phone auth, admin 2FA SMS/email/backup flows.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pymongo
import pyotp
import pytest
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / "frontend" / ".env")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import server
import sms_otp
import sms_service


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
JWT_SECRET = os.environ.get("JWT_SECRET")
if not BASE_URL or not MONGO_URL or not DB_NAME or not JWT_SECRET:
    raise RuntimeError("Required env missing for tests")

API = f"{BASE_URL.rstrip('/')}/api"


def _mongo_sync(db_name: str | None = None):
    return pymongo.MongoClient(MONGO_URL)[db_name or DB_NAME]


@pytest.fixture
def cleanup_runtime_members():
    yield
    _mongo_sync().users.delete_many({"email": {"$regex": r"^thr_[a-f0-9]{8}@example\.com$"}})


class TestLoginThrottleAndCorsExternal:
    """External API checks for throttle wiring and CORS behavior."""

    def test_user_login_throttle_returns_429_with_retry_after(self):
        email = f"thr_{uuid.uuid4().hex[:8]}@example.com"
        payload = {"email": email, "password": "Wrong1!pass"}
        for _ in range(10):
            r = requests.post(f"{API}/auth/login", json=payload, timeout=20)
            assert r.status_code == 401
        blocked = requests.post(f"{API}/auth/login", json=payload, timeout=20)
        assert blocked.status_code == 429
        assert blocked.headers.get("Retry-After")

    def test_role_buckets_are_isolated_between_user_and_admin(self):
        shared = f"iso_{uuid.uuid4().hex[:8]}@example.com"
        for _ in range(10):
            user_fail = requests.post(
                f"{API}/auth/login", json={"email": shared, "password": "Wrong1!pass"}, timeout=20
            )
            assert user_fail.status_code == 401

        admin_first = requests.post(
            f"{API}/admin/login", json={"username": shared, "password": "Wrong1!pass"}, timeout=20
        )
        assert admin_first.status_code == 401

    def test_user_success_resets_attempt_counter(self, cleanup_runtime_members):
        email = f"thr_{uuid.uuid4().hex[:8]}@example.com"
        password = "Aa1!goodpass"
        reg = requests.post(
            f"{API}/auth/register",
            json={"fullName": "Throttle Reset", "email": email, "password": password, "subscribeNewsletter": False},
            timeout=20,
        )
        assert reg.status_code == 200, reg.text

        for _ in range(3):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Wrong1!pass"}, timeout=20)
            assert r.status_code == 401

        ok = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
        assert ok.status_code == 200, ok.text
        assert isinstance(ok.json().get("token"), str)

        for _ in range(10):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Wrong1!pass"}, timeout=20)
            assert r.status_code == 401

        blocked = requests.post(f"{API}/auth/login", json={"email": email, "password": "Wrong1!pass"}, timeout=20)
        assert blocked.status_code == 429

    def test_cors_preflight_allows_trusted_origin_and_blocks_untrusted(self):
        trusted = os.environ["CORS_ORIGINS"].split(",")[-1].strip()
        headers = {
            "Origin": trusted,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        ok = requests.options(f"{API}/auth/login", headers=headers, timeout=20)
        assert ok.status_code in (200, 204)
        assert ok.headers.get("access-control-allow-origin") == trusted

        bad = requests.options(
            f"{API}/auth/login",
            headers={**headers, "Origin": "https://evil.invalid"},
            timeout=20,
        )
        assert bad.status_code in (400, 403)
        assert bad.headers.get("access-control-allow-origin") != "https://evil.invalid"

    def test_missing_twilio_config_returns_sanitized_503_message(self):
        r = requests.post(f"{API}/auth/phone/send", json={"phone": "+14155550123"}, timeout=20)
        assert r.status_code == 503
        detail = (r.json().get("detail") or "").lower()
        assert "not configured" in detail or "unavailable" in detail
        assert "twilio_account_sid" not in detail
        assert "twilio_auth_token" not in detail


class _AsyncCollection:
    def __init__(self, inner):
        self.inner = inner

    async def create_index(self, *args, **kwargs):
        return self.inner.create_index(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        return self.inner.find_one(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        return self.inner.update_one(*args, **kwargs)

    async def find_one_and_update(self, *args, **kwargs):
        return self.inner.find_one_and_update(*args, **kwargs)

    async def insert_one(self, *args, **kwargs):
        return self.inner.insert_one(*args, **kwargs)

    async def delete_one(self, *args, **kwargs):
        return self.inner.delete_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self.inner.delete_many(*args, **kwargs)


class _AsyncDB:
    def __init__(self, sync_db):
        self._sync = sync_db
        self.admins = _AsyncCollection(sync_db.admins)
        self.users = _AsyncCollection(sync_db.users)
        self.phone_otps = _AsyncCollection(sync_db.phone_otps)
        self.admin_sms_otps = _AsyncCollection(sync_db.admin_sms_otps)
        self.admin_phone_verify = _AsyncCollection(sync_db.admin_phone_verify)
        self.sms_send_limits = _AsyncCollection(sync_db.sms_send_limits)
        self.password_attempts = _AsyncCollection(sync_db.password_attempts)
        self.admin_trusted_devices = _AsyncCollection(sync_db.admin_trusted_devices)
        self.admin_email_otps = _AsyncCollection(sync_db.admin_email_otps)


@pytest.fixture
def isolated_server_db(monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    client = pymongo.MongoClient(MONGO_URL)
    sync_db = client[f"{DB_NAME}_isolated_{suffix}"]
    for coll_name in [
        "phone_otps",
        "admin_sms_otps",
        "admin_phone_verify",
        "sms_send_limits",
        "password_attempts",
        "admin_trusted_devices",
        "admin_email_otps",
    ]:
        sync_db[coll_name].create_index("expires_at", expireAfterSeconds=0)

    adb = _AsyncDB(sync_db)
    monkeypatch.setattr(server, "db", adb)
    try:
        yield sync_db
    finally:
        client.drop_database(sync_db.name)
        client.close()


def _admin_doc(username: str, password: str, **overrides) -> dict:
    base = {
        "_id": str(uuid.uuid4()),
        "username": username,
        "email": f"{username}@example.com",
        "passwordHash": server.hash_password(password),
        "permissions": server.ALL_PERMS.copy(),
        "isSuper": False,
        "twoFactorEnabled": True,
        "twoFactorSecret": pyotp.random_base32(),
        "twoFactorBackupCodes": [server.hash_password("ABCD1234")],
        "phone": "+14155550123",
        "phoneVerifiedAt": datetime.now(timezone.utc).isoformat(),
        "createdAt": datetime.utcnow().isoformat(),
    }
    base.update(overrides)
    return base


def _run(coro):
    return asyncio.run(coro)


class TestIsolatedPositiveFlowsAndOtpGaps:
    """In-process route tests with isolated DB and TEST-ONLY mocked transport."""

    def test_member_phone_positive_legacy_preserve_and_banned_denied(self, isolated_server_db, monkeypatch):
        legacy_id = str(uuid.uuid4())
        isolated_server_db.users.insert_one(
            {
                "_id": legacy_id,
                "fullName": "Legacy Member",
                "email": "",
                "phone": "4155550123",
                "passwordHash": "",
                "favorites": ["cross-faith"],
                "isBanned": False,
                "createdAt": datetime.utcnow().isoformat(),
            }
        )
        isolated_server_db.users.insert_one(
            {
                "_id": str(uuid.uuid4()),
                "fullName": "Banned",
                "email": "",
                "phone": "+14155550000",
                "passwordHash": "",
                "favorites": [],
                "isBanned": True,
                "createdAt": datetime.utcnow().isoformat(),
            }
        )

        monkeypatch.setattr(sms_otp, "require_sms_config", lambda: ("AC", "tok", {"from_": "+15550001111"}))
        monkeypatch.setattr(sms_otp.secrets, "randbelow", lambda _: 123456)

        sent = []

        async def fake_send_sms(phone: str, text: str) -> str:
            sent.append((phone, text))
            return "SMok"

        monkeypatch.setattr(sms_otp, "send_sms", fake_send_sms)

        async def scenario():
            import httpx

            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                send_r = await c.post("/api/auth/phone/send", json={"phone": "(415) 555-0123"})
                assert send_r.status_code == 200

                verify_r = await c.post("/api/auth/phone/verify", json={"phone": "+1 (415) 555-0123", "code": "123456"})
                assert verify_r.status_code == 200
                data = verify_r.json()
                assert data["user"]["id"] == legacy_id
                assert "cross-faith" in data["user"]["favorites"]

                banned_send = await c.post("/api/auth/phone/send", json={"phone": "+14155550000"})
                assert banned_send.status_code == 200
                banned_verify = await c.post("/api/auth/phone/verify", json={"phone": "+14155550000", "code": "123456"})
                assert banned_verify.status_code == 403

        _run(scenario())
        updated = isolated_server_db.users.find_one({"_id": legacy_id})
        assert updated["phone"] == "+14155550123"
        assert len(sent) >= 2

    def test_admin_sms_challenge_trust_remove_and_reset_revoke(self, isolated_server_db, monkeypatch):
        admin = _admin_doc("dispadmin", "Aa1!aaaa")
        super_admin = _admin_doc("superadmin", "Aa1!aaaa", isSuper=True)
        target = _admin_doc("targetadmin", "Aa1!aaaa")
        isolated_server_db.admins.insert_many([admin, super_admin, target])

        monkeypatch.setattr(sms_otp, "require_sms_config", lambda: ("AC", "tok", {"from_": "+15550001111"}))
        monkeypatch.setattr(sms_otp.secrets, "randbelow", lambda _: 123456)

        async def fake_send_sms(_phone: str, _text: str) -> str:
            return "SMok"

        monkeypatch.setattr(sms_otp, "send_sms", fake_send_sms)

        async def scenario():
            import httpx

            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                login = await c.post("/api/admin/login", json={"username": "dispadmin", "password": "Aa1!aaaa"})
                assert login.status_code == 200
                challenge = login.json()["twoFactorToken"]

                send = await c.post("/api/admin/2fa/sms/send", headers={"Authorization": f"Bearer {challenge}"})
                assert send.status_code == 200

                sms_ok = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "sms", "code": "123456", "trustDevice": True},
                    headers={"Authorization": f"Bearer {challenge}"},
                )
                assert sms_ok.status_code == 200
                full_token = sms_ok.json()["token"]
                trust_token = sms_ok.json().get("trustDeviceToken")
                assert trust_token

                trusted_login = await c.post(
                    "/api/admin/login",
                    json={"username": "dispadmin", "password": "Aa1!aaaa"},
                    headers={"X-Admin-Trust-Token": trust_token},
                )
                assert trusted_login.status_code == 200
                assert trusted_login.json()["status"] == "ok"

                login2 = await c.post("/api/admin/login", json={"username": "dispadmin", "password": "Aa1!aaaa"})
                challenge2 = login2.json()["twoFactorToken"]

                # Keep this test fast by bypassing resend cooldown for the already-used OTP row.
                isolated_server_db.admin_sms_otps.update_one(
                    {"_id": admin["_id"]},
                    {"$set": {"sent_at": datetime.now(timezone.utc) - timedelta(seconds=61)}},
                )
                send2 = await c.post("/api/admin/2fa/sms/send", headers={"Authorization": f"Bearer {challenge2}"})
                assert send2.status_code == 200

                removed = await c.delete("/api/admin/me/phone", headers={"Authorization": f"Bearer {full_token}"})
                assert removed.status_code == 200

                after_remove = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "sms", "code": "123456"},
                    headers={"Authorization": f"Bearer {challenge2}"},
                )
                assert after_remove.status_code == 401

                tgt_login = await c.post("/api/admin/login", json={"username": "targetadmin", "password": "Aa1!aaaa"})
                tgt_challenge = tgt_login.json()["twoFactorToken"]
                tgt_send = await c.post("/api/admin/2fa/sms/send", headers={"Authorization": f"Bearer {tgt_challenge}"})
                assert tgt_send.status_code == 200

                super_token = server.make_token(super_admin["_id"], True, server.ALL_PERMS.copy(), super_admin["username"], "admin")
                reset = await c.post(
                    f"/api/admin/2fa/reset/{target['_id']}",
                    headers={"Authorization": f"Bearer {super_token}"},
                )
                assert reset.status_code == 200

                after_reset = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "sms", "code": "123456"},
                    headers={"Authorization": f"Bearer {tgt_challenge}"},
                )
                assert after_reset.status_code == 400

        _run(scenario())
        assert isolated_server_db.admin_sms_otps.find_one({"_id": target["_id"]}) is None

    def test_admin_email_totp_backup_and_sms_error_sanitization(self, isolated_server_db, monkeypatch):
        admin = _admin_doc("mailadmin", "Aa1!aaaa")
        isolated_server_db.admins.insert_one(admin)

        sent_mail = {}

        async def fake_send_email(to_email: str, _subject: str, html: str, **_kwargs):
            sent_mail["to"] = to_email
            sent_mail["html"] = html

        monkeypatch.setattr(server, "send_email", fake_send_email)
        monkeypatch.setattr(server, "_new_email_otp", lambda: "654321")
        monkeypatch.setattr(server, "SMTP_USER", "test@example.com")
        monkeypatch.setattr(server, "SMTP_PASS", "x")

        async def scenario():
            import httpx

            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                login = await c.post("/api/admin/login", json={"username": "mailadmin", "password": "Aa1!aaaa"})
                challenge = login.json()["twoFactorToken"]

                email_send = await c.post("/api/admin/2fa/email/send", headers={"Authorization": f"Bearer {challenge}"})
                assert email_send.status_code == 200
                assert sent_mail.get("to") == admin["email"]

                email_ok = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "email", "code": "654321"},
                    headers={"Authorization": f"Bearer {challenge}"},
                )
                assert email_ok.status_code == 200

                login2 = await c.post("/api/admin/login", json={"username": "mailadmin", "password": "Aa1!aaaa"})
                challenge2 = login2.json()["twoFactorToken"]
                backup_ok = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "backup", "code": "ABCD-1234"},
                    headers={"Authorization": f"Bearer {challenge2}"},
                )
                assert backup_ok.status_code == 200

                login3 = await c.post("/api/admin/login", json={"username": "mailadmin", "password": "Aa1!aaaa"})
                challenge3 = login3.json()["twoFactorToken"]
                backup_reuse = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "backup", "code": "ABCD-1234"},
                    headers={"Authorization": f"Bearer {challenge3}"},
                )
                assert backup_reuse.status_code == 401

                login4 = await c.post("/api/admin/login", json={"username": "mailadmin", "password": "Aa1!aaaa"})
                challenge4 = login4.json()["twoFactorToken"]
                totp_code = pyotp.TOTP(admin["twoFactorSecret"]).now()
                totp_ok = await c.post(
                    "/api/admin/2fa/login",
                    json={"method": "totp", "code": totp_code},
                    headers={"Authorization": f"Bearer {challenge4}"},
                )
                assert totp_ok.status_code == 200

        _run(scenario())

        class _TimeoutMessages:
            def create(self, **_kwargs):
                raise RequestException("timeout internals")

        class _TimeoutClient:
            def __init__(self, _sid, _token, http_client=None):
                self.messages = _TimeoutMessages()

        monkeypatch.setattr(sms_service, "Client", _TimeoutClient)
        monkeypatch.setattr(sms_service, "require_sms_config", lambda: ("AC", "tok", {"from_": "+15550001111"}))
        with pytest.raises(Exception) as ex:
            _run(sms_service.send_sms("+14155550123", "hello"))
        assert "did not respond" in str(ex.value).lower() or "unavailable" in str(ex.value).lower()

    def test_otp_edge_cases_normalization_resend_concurrency_and_limits(self, isolated_server_db, monkeypatch):
        monkeypatch.setattr(sms_otp, "require_sms_config", lambda: ("AC", "tok", {"from_": "+15550001111"}))
        monkeypatch.setattr(sms_otp.secrets, "randbelow", lambda _: 123456)

        sent = {"count": 0}

        async def fake_send_sms(_phone: str, _text: str) -> str:
            sent["count"] += 1
            return f"SM{sent['count']}"

        monkeypatch.setattr(sms_otp, "send_sms", fake_send_sms)

        db = _AsyncDB(isolated_server_db)
        coll = db.phone_otps

        # Expired + legacy-provider records are unusable
        isolated_server_db.phone_otps.insert_one(
            {
                "_id": "expired",
                "provider": "twilio",
                "ready": True,
                "phone": "+14155550123",
                "nonce": "n1",
                "code_hash": server.hash_password("123456"),
                "attempts": 0,
                "sent_at": datetime.now(timezone.utc) - timedelta(minutes=20),
                "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1),
            }
        )
        isolated_server_db.phone_otps.insert_one(
            {
                "_id": "legacy",
                "provider": "email_gateway",
                "ready": True,
                "phone": "+14155550123",
                "nonce": "n2",
                "code_hash": server.hash_password("123456"),
                "attempts": 0,
                "sent_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
        )
        assert _run(sms_otp.consume_code(coll, "expired", "123456", "+14155550123")) is None
        assert _run(sms_otp.consume_code(coll, "legacy", "123456", "+14155550123")) is None

        # Number normalization accepts local + international formats (no carrier/type checks)
        assert sms_service.normalize_phone("(415) 555-0123") == "+14155550123"
        assert sms_service.normalize_phone("+44 20 7946 0958").startswith("+44")

        async def race_send():
            return await asyncio.gather(
                sms_otp.send_code(db, coll, "same-key", "+14155550999", "sign-in"),
                sms_otp.send_code(db, coll, "same-key", "+14155550999", "sign-in"),
                return_exceptions=True,
            )

        race = _run(race_send())
        successes = [r for r in race if isinstance(r, dict)]
        failures = [r for r in race if isinstance(r, Exception)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert sent["count"] == 1

        for i in range(5):
            _run(sms_otp.send_code(db, coll, f"num-limit-{i}", "+14155558888", "sign-in"))
        with pytest.raises(Exception):
            _run(sms_otp.send_code(db, coll, "num-limit-6", "+14155558888", "sign-in"))

        # Burn through global bucket after earlier sends in this test.
        for i in range(94):
            _run(sms_otp.send_code(db, coll, f"g-{i}", f"+1415666{1000 + i}", "sign-in"))
        with pytest.raises(Exception):
            _run(sms_otp.send_code(db, coll, "g-over", "+14157779999", "sign-in"))
