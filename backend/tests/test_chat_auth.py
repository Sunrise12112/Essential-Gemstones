"""Backend tests for AI chat member-only gating.

Coverage:
- Public modes (ask-luca, stone-guide) require member auth (user or admin JWT)
- Anonymous requests to /api/chat/stream and session endpoints return 401
- Registered user can stream, list, get, rename, delete their own sessions
- Cross-user isolation: user A cannot access user B session (403)
- admin-writer mode still works for admin token, rejects user token (403) and anon (401)
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://gemstone-makeover.preview.emergentagent.com"
API = f"{BASE_URL}/api"

ADMIN_USERNAME = "admin"  # From memory/test_credentials.md — master password login
ADMIN_PASSWORD = "1121211221"


# ---------- fixtures ---------- #

@pytest.fixture(scope="module")
def admin_token() -> str:
    # Try master password login (no username)
    r = requests.post(f"{API}/admin/login", json={"password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin master login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _register_user(email_prefix: str = "TEST_chat") -> dict:
    email = f"{email_prefix}_{uuid.uuid4().hex[:10]}@example.com"
    payload = {
        "fullName": "Test Chat User",
        "email": email,
        "password": "testpass123",
        "subscribeNewsletter": False,
    }
    r = requests.post(f"{API}/auth/register", json=payload, timeout=20)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"token": data["token"], "user": data["user"], "email": email}


@pytest.fixture(scope="module")
def user_a() -> dict:
    return _register_user("TEST_userA")


@pytest.fixture(scope="module")
def user_b() -> dict:
    return _register_user("TEST_userB")


# ---------- 401 for anonymous ---------- #

class TestAnonymousBlocked:

    def test_stream_askluca_no_auth_401(self):
        r = requests.post(f"{API}/chat/stream", json={"mode": "ask-luca", "message": "hi"}, timeout=15)
        assert r.status_code == 401
        assert "sign in" in r.text.lower()

    def test_stream_stoneguide_no_auth_401(self):
        r = requests.post(f"{API}/chat/stream", json={"mode": "stone-guide", "message": "hi"}, timeout=15)
        assert r.status_code == 401

    def test_list_sessions_no_auth_401(self):
        r = requests.get(f"{API}/chat/sessions?mode=ask-luca", timeout=15)
        assert r.status_code == 401

    def test_get_session_no_auth_401(self):
        r = requests.get(f"{API}/chat/session/{uuid.uuid4()}", timeout=15)
        assert r.status_code == 401

    def test_rename_session_no_auth_401(self):
        r = requests.put(f"{API}/chat/session/{uuid.uuid4()}", json={"title": "x"}, timeout=15)
        assert r.status_code == 401

    def test_delete_session_no_auth_401(self):
        r = requests.delete(f"{API}/chat/session/{uuid.uuid4()}", timeout=15)
        assert r.status_code == 401


# ---------- user stream + session CRUD ---------- #

class TestMemberChatFlow:

    def _stream_message(self, token: str, mode: str, message: str, session_id: str | None = None) -> tuple[str, str]:
        """Consume SSE and return (session_id, full_reply)."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {"mode": mode, "message": message}
        if session_id:
            body["sessionId"] = session_id
        with requests.post(f"{API}/chat/stream", json=body, headers=headers, stream=True, timeout=90) as r:
            assert r.status_code == 200, f"stream returned {r.status_code}: {r.text}"
            sid = None
            reply = ""
            saw_done = False
            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                if raw_line.startswith("event: session"):
                    # next data line contains id
                    continue
                if raw_line.startswith("event: done"):
                    saw_done = True
                if raw_line.startswith("data:"):
                    payload = raw_line[5:].strip()
                    # heuristic: first data after event:session is the session id
                    if sid is None and len(payload) >= 8 and "-" in payload:
                        sid = payload
                        continue
                    if payload == "end":
                        continue
                    reply += payload.replace("\\n", "\n")
            assert sid, "Did not receive session id"
            assert saw_done, "Stream did not end with event: done"
            return sid, reply

    def test_user_can_stream_askluca(self, user_a):
        sid, reply = self._stream_message(user_a["token"], "ask-luca", "How do I care for my bracelet?")
        assert len(reply.strip()) > 0
        user_a["session_id"] = sid

    def test_user_can_list_sessions(self, user_a):
        assert "session_id" in user_a, "Precondition streaming test must run first"
        headers = {"Authorization": f"Bearer {user_a['token']}"}
        r = requests.get(f"{API}/chat/sessions?mode=ask-luca", headers=headers, timeout=15)
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list)
        ids = [s["id"] for s in sessions]
        assert user_a["session_id"] in ids

    def test_user_can_get_session(self, user_a):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_a['token']}"}
        r = requests.get(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == sid
        assert data["mode"] == "ask-luca"
        assert isinstance(data.get("messages"), list)
        assert len(data["messages"]) >= 2  # user + assistant

    def test_user_can_rename_session(self, user_a):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_a['token']}", "Content-Type": "application/json"}
        r = requests.put(f"{API}/chat/session/{sid}", json={"title": "TEST renamed chat"}, headers=headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("title") == "TEST renamed chat"

        # Verify persisted
        r2 = requests.get(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["title"] == "TEST renamed chat"

    def test_cross_user_isolation_get(self, user_a, user_b):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_b['token']}"}
        r = requests.get(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r.status_code == 403

    def test_cross_user_isolation_rename(self, user_a, user_b):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_b['token']}", "Content-Type": "application/json"}
        r = requests.put(f"{API}/chat/session/{sid}", json={"title": "hijack"}, headers=headers, timeout=15)
        assert r.status_code == 403

    def test_cross_user_isolation_delete(self, user_a, user_b):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_b['token']}"}
        r = requests.delete(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r.status_code == 403

    def test_user_can_delete_own_session(self, user_a):
        sid = user_a["session_id"]
        headers = {"Authorization": f"Bearer {user_a['token']}"}
        r = requests.delete(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r.status_code == 200

        # Now GET should return 404
        r2 = requests.get(f"{API}/chat/session/{sid}", headers=headers, timeout=15)
        assert r2.status_code == 404


# ---------- admin-writer ---------- #

class TestAdminWriter:

    def test_admin_writer_no_auth_401(self):
        r = requests.post(f"{API}/chat/stream", json={"mode": "admin-writer", "message": "hi"}, timeout=15)
        assert r.status_code == 401

    def test_admin_writer_with_user_token_403(self, user_a):
        headers = {"Authorization": f"Bearer {user_a['token']}", "Content-Type": "application/json"}
        r = requests.post(f"{API}/chat/stream", json={"mode": "admin-writer", "message": "hi"}, headers=headers, timeout=15)
        assert r.status_code == 403

    def test_admin_writer_with_admin_token_streams(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        body = {"mode": "admin-writer", "message": "Write a 6-word tagline about lava stone."}
        with requests.post(f"{API}/chat/stream", json=body, headers=headers, stream=True, timeout=90) as r:
            assert r.status_code == 200, f"admin-writer stream failed: {r.status_code} {r.text}"
            saw_session = False
            saw_data = False
            saw_done = False
            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                if raw_line.startswith("event: session"):
                    saw_session = True
                if raw_line.startswith("event: done"):
                    saw_done = True
                if raw_line.startswith("data:"):
                    saw_data = True
            assert saw_session and saw_data and saw_done
