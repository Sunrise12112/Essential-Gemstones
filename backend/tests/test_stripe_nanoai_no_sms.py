"""Regression tests for: (1) Stripe checkout, (2) Nano AI CMS, (3) SMS removal, (4) TOTP 2FA still works."""
import os, pyotp, pytest, requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE:
    # fall back to reading frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
                break

ADMIN_USER = "master"
ADMIN_PASS = "1121211221"
TOTP_SECRET = "IVQKJZDYWPOQ4ZAXNKMNU22TQ5N5DL7U"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "needs_2fa", d
    tft = d["twoFactorToken"]
    methods = d.get("availableMethods") or []
    assert "totp" in methods
    assert "sms" not in methods, f"SMS should be gone from availableMethods, got {methods}"
    assert "phoneHint" not in d, f"phoneHint should be absent, got {d.get('phoneHint')}"
    code = pyotp.TOTP(TOTP_SECRET).now()
    r2 = requests.post(f"{BASE}/api/admin/2fa/login",
                       json={"twoFactorToken": tft, "code": code, "method": "totp"},
                       headers={"Authorization": f"Bearer {tft}"})
    assert r2.status_code == 200, r2.text
    tok = r2.json()["token"]
    assert isinstance(tok, str) and len(tok) > 10
    return tok


# ---------------- Stripe checkout ----------------
class TestStripeCheckout:
    def test_checkout_chakra_success(self):
        r = requests.post(f"{BASE}/api/payments/checkout",
                          json={"product_id": "chakra", "origin_url": BASE})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout_url" in d and d["checkout_url"].startswith("https://")
        assert "checkout.stripe.com" in d["checkout_url"], d["checkout_url"]
        assert "session_id" in d and d["session_id"].startswith("cs_")
        # status endpoint
        s = requests.get(f"{BASE}/api/payments/status/{d['session_id']}")
        assert s.status_code == 200, s.text
        sd = s.json()
        assert sd["session_id"] == d["session_id"]
        assert sd["payment_status"] in ("pending", "unpaid", "no_payment_required")
        assert "product_name" in sd
        # chakra $28.00 -> 2800 cents
        assert sd["amount"] == 2800, f"expected 2800 cents got {sd['amount']}"

    def test_checkout_invalid_product(self):
        r = requests.post(f"{BASE}/api/payments/checkout",
                          json={"product_id": "does-not-exist-xyz", "origin_url": BASE})
        assert r.status_code == 404, r.text


# ---------------- SMS endpoints removed ----------------
class TestSmsGone:
    @pytest.mark.parametrize("method,path,body", [
        ("POST", "/api/auth/phone/send", {"phone": "+14155550123"}),
        ("POST", "/api/auth/phone/verify", {"phone": "+14155550123", "code": "123456"}),
        ("POST", "/api/admin/2fa/sms/send", {"twoFactorToken": "x"}),
        ("PUT",  "/api/admin/me/phone",   {"phone": "+14155550123"}),
    ])
    def test_sms_endpoint_gone(self, method, path, body):
        r = requests.request(method, f"{BASE}{path}", json=body)
        assert r.status_code == 404, f"{method} {path} expected 404 got {r.status_code}: {r.text[:200]}"


# ---------------- Nano AI section CMS ----------------
class TestNanoAI:
    def test_site_has_nanoai(self):
        r = requests.get(f"{BASE}/api/site")
        assert r.status_code == 200
        d = r.json()
        assert "nanoAI" in d, d.keys()
        na = d["nanoAI"]
        assert "title" in na and na["title"]
        assert "ctaUrl" in na
        assert "features" in na and isinstance(na["features"], list)
        assert "nanoAI" in d.get("sectionOrder", []), d.get("sectionOrder")

    def test_admin_edit_nanoai(self, admin_token):
        original = requests.get(f"{BASE}/api/site").json()
        new_title = "Meet Nano AI TEST_EDIT"
        payload = dict(original)
        payload["nanoAI"] = dict(original["nanoAI"])
        payload["nanoAI"]["title"] = new_title
        r = requests.put(f"{BASE}/api/site", json=payload,
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, r.text
        after = requests.get(f"{BASE}/api/site").json()
        assert after["nanoAI"]["title"] == new_title
        # restore
        payload["nanoAI"]["title"] = original["nanoAI"]["title"]
        requests.put(f"{BASE}/api/site", json=payload,
                     headers={"Authorization": f"Bearer {admin_token}"})
