"""Phone/SMS auth coverage for Twilio-configured OTP flows and auth guards.

Covers:
- Public API behavior for /api/auth/phone/send and /api/auth/phone/verify
- Admin challenge-route token guards for SMS challenge endpoint
- Twilio transport parameter/error handling via TEST-ONLY mocks
- SMS OTP persistence/consumption behavior with isolated Mongo collections
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import pymongo
import pytest
import requests
from fastapi import HTTPException
from requests import Response
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / "frontend" / ".env")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sms_otp import MAX_ATTEMPTS, RESEND_SECONDS, consume_code, send_code
import sms_otp as sms_otp_module
import sms_service


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL is required for API tests")
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
JWT_SECRET = os.environ.get("JWT_SECRET")
if not MONGO_URL or not DB_NAME or not JWT_SECRET:
    raise RuntimeError("MONGO_URL, DB_NAME and JWT_SECRET are required")


def _mongo_sync():
    return pymongo.MongoClient(MONGO_URL)[DB_NAME]


def _master_admin_doc() -> dict:
    doc = _mongo_sync().admins.find_one({"username": "master"})
    assert doc is not None, "master admin must exist"
    return doc


def _full_admin_token() -> str:
    admin = _master_admin_doc()
    payload = {
        "sub": admin["_id"],
        "username": admin["username"],
        "role": "admin",
        "isSuper": bool(admin.get("isSuper")),
        "permissions": admin.get("permissions", []),
        "purpose": "full",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=7)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _setup_2fa_token() -> str:
    admin = _master_admin_doc()
    payload = {
        "sub": admin["_id"],
        "username": admin["username"],
        "role": "admin",
        "purpose": "setup2fa",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _member_token(email: str = "sms-test-user@example.com") -> str:
    sub = f"TEST_member_{uuid.uuid4().hex[:8]}"
    _mongo_sync().users.insert_one(
        {
            "_id": sub,
            "fullName": "SMS Member",
            "email": email,
            "passwordHash": "",
            "isBanned": False,
            "favorites": [],
            "createdAt": datetime.utcnow().isoformat(),
        }
    )
    payload = {
        "sub": sub,
        "email": email,
        "role": "user",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=7)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def _cleanup_test_users():
    yield
    _mongo_sync().users.delete_many({"_id": {"$regex": "^TEST_member_"}})
    _mongo_sync().users.delete_many({"email": {"$regex": "^smsreg_.*@example\\.com$"}})


class TestPhoneAuthApi:
    """Public member phone auth endpoint checks."""

    def test_phone_send_malformed_number_returns_400(self):
        r: Response = requests.post(f"{API}/auth/phone/send", json={"phone": "abc"}, timeout=20)
        assert r.status_code == 400
        data = r.json()
        assert "valid phone" in data["detail"].lower()

    def test_phone_send_valid_number_without_credentials_returns_503(self):
        r: Response = requests.post(f"{API}/auth/phone/send", json={"phone": "+14155550123"}, timeout=20)
        assert r.status_code == 503
        data = r.json()
        assert "not configured" in data["detail"].lower() or "unavailable" in data["detail"].lower()

    def test_phone_send_local_us_format_normalizes_then_returns_503(self):
        r: Response = requests.post(f"{API}/auth/phone/send", json={"phone": "(415) 555-0123"}, timeout=20)
        assert r.status_code == 503
        assert "text" in r.json()["detail"].lower()

    def test_phone_verify_without_pending_code_returns_401(self):
        r: Response = requests.post(
            f"{API}/auth/phone/verify",
            json={"phone": "+14155550123", "code": "123456"},
            timeout=20,
        )
        assert r.status_code == 401
        assert "invalid or expired" in r.json()["detail"].lower()


class TestExistingAuthRegression:
    """Regression checks for existing non-SMS member and Google-session auth."""

    def test_email_register_login_and_auth_me(self):
        email = f"smsreg_{uuid.uuid4().hex[:8]}@example.com"
        password = "Aa1!aaaa"

        reg = requests.post(
            f"{API}/auth/register",
            json={
                "fullName": "SMS Regression",
                "email": email,
                "password": password,
                "subscribeNewsletter": False,
            },
            timeout=20,
        )
        assert reg.status_code == 200, reg.text
        reg_data = reg.json()
        assert isinstance(reg_data.get("token"), str)
        assert reg_data["user"]["email"] == email

        login = requests.post(
            f"{API}/auth/login",
            json={"email": email, "password": password},
            timeout=20,
        )
        assert login.status_code == 200, login.text
        token = login.json()["token"]

        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=20)
        assert me.status_code == 200, me.text
        me_data = me.json()
        assert me_data["user"]["email"] == email
        assert me_data["user"]["fullName"] == "SMS Regression"

    def test_google_session_invalid_returns_401(self):
        r = requests.post(
            f"{API}/auth/google/session",
            json={"session_id": "definitely-invalid-session-id"},
            timeout=20,
        )
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower() or "try again" in r.json()["detail"].lower()


class TestAdminSmsChallengeTokenGuards:
    """Guard checks so non-challenge tokens cannot access SMS challenge routes."""

    def test_full_admin_token_rejected_for_admin_2fa_sms_send(self):
        token = _full_admin_token()
        r = requests.post(
            f"{API}/admin/2fa/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 401
        assert "challenge" in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()

    def test_setup_token_rejected_for_admin_2fa_sms_send(self):
        token = _setup_2fa_token()
        r = requests.post(
            f"{API}/admin/2fa/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 401

    def test_member_token_rejected_for_admin_2fa_sms_send(self):
        token = _member_token()
        r = requests.post(
            f"{API}/admin/2fa/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 401


class _FakeTwilioMessage:
    def __init__(self, sid: str = "SM123", status: str = "queued"):
        self.sid = sid
        self.status = status


class _FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeTwilioMessage()


class _FakeClient:
    def __init__(self, sid, token, http_client=None):
        self.sid = sid
        self.token = token
        self.http_client = http_client
        self.messages = _FakeMessages()


class TestTwilioTransportUnit:
    """Unit checks for Twilio transport semantics using TEST-ONLY mocks."""

    def test_send_sms_uses_to_body_and_from_sender_fields(self, monkeypatch):
        monkeypatch.setattr(sms_service, "require_sms_config", lambda: ("AC123", "tok", {"from_": "+15550001111"}))
        monkeypatch.setattr(sms_service, "normalize_phone", lambda _: "+14155550123")

        holder = {}

        def fake_client_factory(sid, token, http_client=None):
            c = _FakeClient(sid, token, http_client=http_client)
            holder["client"] = c
            return c

        monkeypatch.setattr(sms_service, "Client", fake_client_factory)

        sid = asyncio.run(sms_service.send_sms("(415) 555-0123", "OTP 123456"))
        assert sid == "SM123"
        call = holder["client"].messages.calls[0]
        assert call["to"] == "+14155550123"
        assert call["body"] == "OTP 123456"
        assert call["from_"] == "+15550001111"

    def test_send_sms_uses_messaging_service_sid_when_configured(self, monkeypatch):
        monkeypatch.setattr(
            sms_service,
            "require_sms_config",
            lambda: ("AC123", "tok", {"messaging_service_sid": "MG123"}),
        )
        monkeypatch.setattr(sms_service, "normalize_phone", lambda _: "+14155550123")

        holder = {}

        def fake_client_factory(sid, token, http_client=None):
            c = _FakeClient(sid, token, http_client=http_client)
            holder["client"] = c
            return c

        monkeypatch.setattr(sms_service, "Client", fake_client_factory)

        asyncio.run(sms_service.send_sms("+14155550123", "OTP 654321"))
        call = holder["client"].messages.calls[0]
        assert call["messaging_service_sid"] == "MG123"
        assert "from_" not in call

    def test_send_sms_maps_known_twilio_error_to_sanitized_message(self, monkeypatch):
        monkeypatch.setattr(sms_service, "require_sms_config", lambda: ("AC123", "tok", {"from_": "+15550001111"}))
        monkeypatch.setattr(sms_service, "normalize_phone", lambda _: "+14155550123")

        class _ErroringMessages:
            def create(self, **kwargs):
                response = Response()
                response.status_code = 400
                raise TwilioRestException(status=400, uri="/Messages", msg="bad", code=21610, method="POST", details=None)

        class _ErrorClient:
            def __init__(self, sid, token, http_client=None):
                self.messages = _ErroringMessages()

        monkeypatch.setattr(sms_service, "Client", _ErrorClient)

        with pytest.raises(HTTPException) as ex:
            asyncio.run(sms_service.send_sms("+14155550123", "OTP"))
        assert ex.value.status_code == 502
        assert "opted out" in ex.value.detail.lower()

    def test_require_sms_config_rejects_missing_or_both_senders(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")

        monkeypatch.setenv("TWILIO_PHONE_NUMBER", "")
        monkeypatch.setenv("TWILIO_MESSAGING_SERVICE_SID", "")
        with pytest.raises(HTTPException) as ex_none:
            sms_service.require_sms_config()
        assert ex_none.value.status_code == 503

        monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
        monkeypatch.setenv("TWILIO_MESSAGING_SERVICE_SID", "MG123")
        with pytest.raises(HTTPException) as ex_both:
            sms_service.require_sms_config()
        assert ex_both.value.status_code == 503


@pytest.fixture
def isolated_sms_collections():
    """Isolated async Mongo collections for sms_otp behavior tests."""
    suffix = uuid.uuid4().hex[:8]
    client = pymongo.MongoClient(MONGO_URL)
    db_sync = client[f"{DB_NAME}_sms_test_{suffix}"]
    coll_sync = db_sync.phone_otps
    coll_sync.create_index("expires_at", expireAfterSeconds=0)
    db_sync.sms_send_limits.create_index("expires_at", expireAfterSeconds=0)

    class AsyncCollection:
        def __init__(self, inner):
            self.inner = inner

        async def create_index(self, *args, **kwargs):
            return self.inner.create_index(*args, **kwargs)

        async def update_one(self, *args, **kwargs):
            return self.inner.update_one(*args, **kwargs)

        async def find_one(self, *args, **kwargs):
            return self.inner.find_one(*args, **kwargs)

        async def find_one_and_update(self, *args, **kwargs):
            return self.inner.find_one_and_update(*args, **kwargs)

        async def insert_one(self, *args, **kwargs):
            return self.inner.insert_one(*args, **kwargs)

    class AsyncDB:
        def __init__(self, inner):
            self.sms_send_limits = AsyncCollection(inner.sms_send_limits)

    db = AsyncDB(db_sync)
    coll = AsyncCollection(coll_sync)
    try:
        yield db, coll
    finally:
        client.drop_database(db_sync.name)
        client.close()


class TestSmsOtpUnit:
    """Unit checks for OTP state transitions and anti-replay behavior."""

    def test_send_code_stores_hash_and_not_plaintext(self, isolated_sms_collections, monkeypatch):
        db, coll = isolated_sms_collections

        async def fake_send_sms(phone: str, text: str) -> str:
            assert phone == "+14155550123"
            assert "code:" in text.lower()
            return "SMabc"

        monkeypatch.setattr(sms_otp_module, "require_sms_config", lambda: ("AC123", "tok", {"from_": "+1555"}))
        monkeypatch.setattr(sms_otp_module, "send_sms", fake_send_sms)

        out = asyncio.run(send_code(db, coll, "k1", "+14155550123", "sign-in"))
        assert out["ok"] is True
        row = asyncio.run(coll.find_one({"_id": "k1"}))
        assert row is not None
        assert row["ready"] is True
        assert row.get("message_sid") == "SMabc"
        assert isinstance(row.get("code_hash"), str)
        assert "$2b$" in row["code_hash"]

    def test_provider_failure_leaves_no_usable_code(self, isolated_sms_collections, monkeypatch):
        db, coll = isolated_sms_collections

        async def fake_send_sms(_phone: str, _text: str) -> str:
            raise HTTPException(status_code=503, detail="Provider down")

        monkeypatch.setattr(sms_otp_module, "require_sms_config", lambda: ("AC123", "tok", {"from_": "+1555"}))
        monkeypatch.setattr(sms_otp_module, "send_sms", fake_send_sms)

        with pytest.raises(HTTPException):
            asyncio.run(send_code(db, coll, "k2", "+14155550123", "sign-in"))
        row = asyncio.run(coll.find_one({"_id": "k2"}))
        assert row is not None
        assert row.get("ready") is False
        assert "code_hash" not in row

    def test_successful_verification_is_single_use_under_parallel_requests(self, isolated_sms_collections):
        _db, coll = isolated_sms_collections
        hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
        asyncio.run(
            coll.insert_one(
            {
                "_id": "k3",
                "provider": "twilio",
                "ready": True,
                "phone": "+14155550123",
                "nonce": "nonce1",
                "code_hash": hashed,
                "attempts": 0,
                "sent_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            }
        )
        )

        async def _run_parallel():
            return await asyncio.gather(
                consume_code(coll, "k3", "123456", "+14155550123"),
                consume_code(coll, "k3", "123456", "+14155550123"),
            )

        r1, r2 = asyncio.run(_run_parallel())
        successes = [r for r in (r1, r2) if r is not None]
        failures = [r for r in (r1, r2) if r is None]
        assert len(successes) == 1
        assert len(failures) == 1

    def test_consumed_code_does_not_bypass_resend_cooldown(self, isolated_sms_collections, monkeypatch):
        db, coll = isolated_sms_collections

        monkeypatch.setattr(sms_otp_module, "require_sms_config", lambda: ("AC123", "tok", {"from_": "+1555"}))

        sent_codes = []

        async def fake_send_sms(_phone: str, text: str) -> str:
            sent_codes.append(text)
            return "SMcool"

        monkeypatch.setattr(sms_otp_module, "send_sms", fake_send_sms)

        asyncio.run(send_code(db, coll, "k4", "+14155550123", "sign-in"))

        row = asyncio.run(coll.find_one({"_id": "k4"}))
        assert row and row.get("code_hash")
        code = sent_codes[0].split("code:")[1].split(".")[0].strip()

        consumed = asyncio.run(consume_code(coll, "k4", code, "+14155550123"))
        assert consumed is not None

        with pytest.raises(HTTPException) as ex:
            asyncio.run(send_code(db, coll, "k4", "+14155550123", "sign-in"))
        assert ex.value.status_code == 429
        assert str(RESEND_SECONDS) in ex.value.detail

    def test_wrong_code_attempt_limit_is_enforced(self, isolated_sms_collections):
        _db, coll = isolated_sms_collections
        hashed = bcrypt.hashpw(b"654321", bcrypt.gensalt()).decode()
        asyncio.run(
            coll.insert_one(
            {
                "_id": "k5",
                "provider": "twilio",
                "ready": True,
                "phone": "+14155550123",
                "nonce": "nonce5",
                "code_hash": hashed,
                "attempts": 0,
                "sent_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            }
        )
        )

        for _ in range(MAX_ATTEMPTS):
            assert asyncio.run(consume_code(coll, "k5", "000000", "+14155550123")) is None
        assert asyncio.run(consume_code(coll, "k5", "654321", "+14155550123")) is None
