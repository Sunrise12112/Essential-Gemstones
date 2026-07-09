"""Regression tests for the two production bugs the user reported:
1. Object-storage backed /api/upload (files must NOT land on local disk).
2. PUT /api/site must persist across a backend restart.
3. GET /api/site deep-merge self-heal (hero must have all default keys).
"""
import io
import os
import time
import subprocess
from pathlib import Path

import jwt
import pytest
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
LOCAL_UPLOAD_DIR = Path("/app/backend/uploads")


def _mint_token() -> str:
    payload = {
        "sub": "test-admin",
        "username": "master",
        "role": "admin",
        "isSuper": True,
        "permissions": [],
        "purpose": "full",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=2)).timestamp()),
    }
    return jwt.encode(payload, os.environ.get("JWT_SECRET", "change-me"), algorithm="HS256")


@pytest.fixture(scope="module")
def token() -> str:
    return _mint_token()


@pytest.fixture(scope="module")
def auth_headers(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Sanity ---
def test_admin_me_accepts_minted_token(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/me", headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["user"]["username"] == "master"
    assert data["user"]["isSuper"] is True


# --- Deep-merge self-heal ---
def test_site_hero_has_all_default_keys():
    r = requests.get(f"{BASE_URL}/api/site", timeout=30)
    assert r.status_code == 200
    hero = r.json().get("hero", {})
    for key in ("kicker", "titleLine1", "mediaType", "mediaUrl"):
        assert key in hero and hero[key], f"hero missing key {key}: {hero}"


# --- Upload: PNG to object storage ---
_PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01\x8dP\xa3\xdc\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _tiny_mp4() -> bytes:
    # Minimal ftyp box; not a playable video but valid file bytes for upload path.
    return (
        b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
        + b"\x00" * 32
    )


def test_upload_png_goes_to_object_storage(auth_headers):
    files = {"file": ("test.png", io.BytesIO(_PNG_1PX), "image/png")}
    r = requests.post(f"{BASE_URL}/api/upload", headers=auth_headers, files=files, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "image"
    assert body["size"] == len(_PNG_1PX)
    assert body["url"].startswith("/api/uploads/")
    name = body["url"].split("/")[-1]

    # File must NOT be on local disk (proves it went to object storage)
    assert not (LOCAL_UPLOAD_DIR / name).exists(), \
        f"file leaked to local disk: {LOCAL_UPLOAD_DIR / name}"

    # Serve back
    g = requests.get(f"{BASE_URL}{body['url']}", timeout=60)
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("image/png")
    assert len(g.content) == len(_PNG_1PX)
    assert g.content == _PNG_1PX


def test_upload_mp4_goes_to_object_storage(auth_headers):
    payload = _tiny_mp4()
    files = {"file": ("test.mp4", io.BytesIO(payload), "video/mp4")}
    r = requests.post(f"{BASE_URL}/api/upload", headers=auth_headers, files=files, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "video"
    assert body["size"] == len(payload)
    name = body["url"].split("/")[-1]
    assert not (LOCAL_UPLOAD_DIR / name).exists()

    g = requests.get(f"{BASE_URL}{body['url']}", timeout=60)
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("video/mp4")
    assert len(g.content) == len(payload)


# --- Site persistence across restart ---
def test_site_put_price_persists_across_restart(auth_headers):
    # Fetch current site
    r = requests.get(f"{BASE_URL}/api/site", timeout=30)
    assert r.status_code == 200
    site = r.json()
    products = site.get("products", {})
    items = products.get("items", [])
    assert items, "expected at least one product"
    original_price = items[0]["price"]
    test_price = "$99.99"

    try:
        # Modify only price on item[0]
        items[0]["price"] = test_price
        put_payload = {"products": {**products, "items": items}}
        p = requests.put(
            f"{BASE_URL}/api/site",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=put_payload,
            timeout=30,
        )
        assert p.status_code == 200, p.text

        # Verify immediately
        r2 = requests.get(f"{BASE_URL}/api/site", timeout=30).json()
        assert r2["products"]["items"][0]["price"] == test_price

        # Restart backend and wait
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
        # Wait for backend to come back up
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                h = requests.get(f"{BASE_URL}/api/", timeout=5)
                if h.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        time.sleep(2)

        r3 = requests.get(f"{BASE_URL}/api/site", timeout=30).json()
        assert r3["products"]["items"][0]["price"] == test_price, \
            f"price reverted after restart: got {r3['products']['items'][0]['price']}"
    finally:
        # Restore
        items[0]["price"] = original_price
        restore_payload = {"products": {**products, "items": items}}
        requests.put(
            f"{BASE_URL}/api/site",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=restore_payload,
            timeout=30,
        )
        # sanity — original restored
        final = requests.get(f"{BASE_URL}/api/site", timeout=30).json()
        assert final["products"]["items"][0]["price"] == original_price
