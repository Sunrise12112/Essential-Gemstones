"""Backend tests for super-admin gating of Admin AI endpoints,
Benefits Quiz schema, AI custom-section creation, and image generation.
"""
import os
import time
import uuid

import pyotp
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
assert BASE_URL

MASTER_USER = "master"
MASTER_PW = "1121211221"
TOTP_SECRET = "IVQKJZDYWPOQ4ZAXNKMNU22TQ5N5DL7U"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def super_token(api):
    r = api.post(f"{BASE_URL}/api/admin/login",
                 json={"username": MASTER_USER, "password": MASTER_PW}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    if data.get("status") == "ok" and data.get("token"):
        return data["token"]
    assert data.get("status") == "needs_2fa", data
    tf = data["twoFactorToken"]
    code = pyotp.TOTP(TOTP_SECRET).now()
    r2 = api.post(
        f"{BASE_URL}/api/admin/2fa/login",
        json={"twoFactorToken": tf, "code": code, "method": "totp"},
        headers={"Authorization": f"Bearer {tf}"},
        timeout=30,
    )
    assert r2.status_code == 200, r2.text
    tok = r2.json().get("token")
    assert tok
    return tok


# ------- Gating: 401 no auth, 403 non-super (user token) -------

AI_ENDPOINTS = [
    ("POST", "/api/admin/ai", {"kind": "chat", "message": "hi"}),
    ("POST", "/api/admin/ai-edit", {"instruction": "noop"}),
    ("POST", "/api/admin/ai-edit/undo", {}),
    ("POST", "/api/admin/ai/email/send", {"subject": "x", "html": "<p>x</p>"}),
]


@pytest.mark.parametrize("method,path,body", AI_ENDPOINTS)
def test_no_auth_401(api, method, path, body):
    r = api.request(method, f"{BASE_URL}{path}", json=body, timeout=20)
    assert r.status_code in (401, 403), f"{path} => {r.status_code} {r.text[:200]}"


@pytest.fixture(scope="module")
def member_token(api):
    email = f"TEST_super_gate_{uuid.uuid4().hex[:8]}@example.com"
    pw = "Aa1!aaaa"
    r = api.post(f"{BASE_URL}/api/auth/register",
                 json={"fullName": "Gate Tester", "email": email, "password": pw}, timeout=30)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    if not tok:
        r2 = api.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": pw}, timeout=30)
        assert r2.status_code == 200, r2.text
        tok = r2.json().get("token") or r2.json().get("access_token")
    assert tok
    return tok


@pytest.mark.parametrize("method,path,body", AI_ENDPOINTS)
def test_member_token_rejected(api, member_token, method, path, body):
    r = api.request(method, f"{BASE_URL}{path}", json=body,
                    headers={"Authorization": f"Bearer {member_token}"}, timeout=20)
    # Member/user tokens must not reach admin super gating paths
    assert r.status_code in (401, 403), f"{path} => {r.status_code} {r.text[:200]}"


# ------- Quiz schema in /api/site -------

def test_site_has_quiz_and_custom_sections(api):
    r = api.get(f"{BASE_URL}/api/site", timeout=20)
    assert r.status_code == 200
    site = r.json()
    assert "quiz" in site
    assert isinstance(site["quiz"].get("questions"), list)
    assert len(site["quiz"]["questions"]) == 9
    for q in site["quiz"]["questions"]:
        assert q.get("q") or q.get("question")
        assert isinstance(q.get("options"), list) and len(q["options"]) >= 2
        assert isinstance(q.get("correctIndex") if "correctIndex" in q else q.get("answer"), int)
    assert "customSections" in site
    assert "quiz" in site.get("sectionOrder", [])


# ------- Super admin can call AI edit (create custom section) + undo -------

def _auth(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def test_ai_edit_creates_custom_section_and_undo(api, super_token):
    heading = f"TEST Care Tips {uuid.uuid4().hex[:6]}"
    payload = {
        "kind": "edit",
        "message": (
            f"Add a new section called Care Tips with a heading '{heading}' and a short paragraph "
            "about wiping with a damp cloth. Put it after the FAQ."
        ),
    }
    r = api.post(f"{BASE_URL}/api/admin/ai", json=payload,
                 headers=_auth(super_token), timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("kind") in ("edit", "site_edit", "site-edit"), data
    # Verify persistence
    site = api.get(f"{BASE_URL}/api/site", timeout=20).json()
    cs = site.get("customSections") or []
    found = any(
        any(b.get("type") == "heading" and heading in (b.get("text") or "")
            for b in (sec.get("blocks") or []))
        for sec in cs
    )
    assert found, f"custom section with heading '{heading}' not found: {cs}"

    # Undo to clean up
    snap = data.get("snapshot") or {}
    u = api.post(f"{BASE_URL}/api/admin/ai-edit/undo", json={"snapshot": snap},
                 headers=_auth(super_token), timeout=30)
    assert u.status_code == 200, u.text


# ------- Super admin can generate an image via kind='image' -------

def test_ai_image_generation(api, super_token):
    payload = {
        "kind": "image",
        "message": "Generate an image of a black lava stone bracelet on mossy volcanic rock in warm light.",
    }
    r = api.post(f"{BASE_URL}/api/admin/ai", json=payload,
                 headers=_auth(super_token), timeout=180)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    assert data.get("kind") == "image", data
    imgs = data.get("images") or ([data.get("imageUrl")] if data.get("imageUrl") else [])
    assert imgs and imgs[0], f"no image returned: {data}"
    url = imgs[0]
    if url.startswith("/"):
        url = BASE_URL + url
    h = requests.get(url, timeout=60)
    assert h.status_code == 200
    assert "image" in h.headers.get("content-type", ""), h.headers
