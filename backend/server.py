"""Essential Gemstones CMS Backend with multi-admin & permissions."""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware
from sms_service import normalize_phone as _normalize_phone, mask_phone as _mask_phone
from sms_otp import PhoneCodeResponse, send_code as send_sms_code, consume_code as consume_sms_code, revoke_admin_codes
from auth_throttle import check_password_attempt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

import io as _io
import base64 as _base64
import requests as _requests
import re as _pw_re
import secrets as _secrets

import pyotp
import qrcode as _qrcode

ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
JWT_SECRET = os.environ["JWT_SECRET"]
if not ADMIN_PASSWORD or not JWT_SECRET:
    raise RuntimeError("Admin password and signing secret must be configured")
JWT_ALG = "HS256"
JWT_DAYS = 30
TOTP_ISSUER = "Essential Gemstones Admin"
BACKUP_CODE_COUNT = 10
TWO_FA_CHALLENGE_MINUTES = 5
SETUP_TOKEN_MINUTES = 30

SECTION_PERMS = [
    "navbar", "hero", "products", "story", "promise", "chakra", "stats",
    "lavaMeaning", "founder", "craft", "faq", "gallery", "vip", "footer",
]
META_PERMS = ["sectionOrder", "sectionVisibility", "manage_admins", "manage_subscribers", "manage_users"]
ALL_PERMS = SECTION_PERMS + META_PERMS

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Essential Gemstones")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
security = HTTPBearer(auto_error=False)

# ---------------- AUTH ---------------- #


class LoginIn(BaseModel):
    username: Optional[str] = None
    password: str


class AdminCreate(BaseModel):
    username: str
    password: str
    email: EmailStr
    permissions: list[str] = []
    isSuper: bool = False


class AdminUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    permissions: Optional[list[str]] = None
    isSuper: Optional[bool] = None


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


PASSWORD_POLICY_MESSAGE = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a lowercase letter, a number, and a symbol."
)


def validate_password_strength(pw: str) -> None:
    """Raise HTTPException 400 if the password doesn't meet policy."""
    if not pw or len(pw) < 8:
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not _pw_re.search(r"[A-Z]", pw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not _pw_re.search(r"[a-z]", pw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not _pw_re.search(r"[0-9]", pw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not _pw_re.search(r"[^A-Za-z0-9]", pw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)


# ---------------- TOTP / 2FA HELPERS ---------------- #


def _new_totp_secret() -> str:
    return pyotp.random_base32()


def _totp_provisioning_uri(username: str, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=TOTP_ISSUER)


def _totp_qr_data_url(uri: str) -> str:
    img = _qrcode.make(uri)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + _base64.b64encode(buf.getvalue()).decode("ascii")


def _verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    code = code.replace(" ", "").strip()
    if not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def _new_backup_codes() -> list[str]:
    # 10 codes formatted as XXXX-XXXX using URL-safe alphanumerics
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        raw = _secrets.token_hex(4).upper()  # 8 hex chars
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes


def _hash_backup_codes(codes: list[str]) -> list[str]:
    return [hash_password(c.replace("-", "").upper()) for c in codes]


def _match_backup_code(input_code: str, hashed_list: list[str]) -> int:
    """Return the index of the matching hashed backup code, or -1."""
    norm = (input_code or "").replace("-", "").upper().strip()
    for i, h in enumerate(hashed_list or []):
        if verify_password(norm, h):
            return i
    return -1


# ---------- Email OTP as an alternative 2FA method ---------- #

EMAIL_OTP_TTL_MINUTES = 10
EMAIL_OTP_MAX_ATTEMPTS = 5
EMAIL_OTP_RESEND_SECONDS = 30


def _new_email_otp() -> str:
    return f"{_secrets.randbelow(1000000):06d}"


def _obfuscate_email(email: str) -> str:
    if not email or "@" not in email:
        return "your inbox"
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = name[0] + "*"
    else:
        masked = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked}@{domain}"


def _email_otp_html(username: str, code: str) -> str:
    return f"""
    <div style="font-family: Georgia, 'Times New Roman', serif; background:#faf6f0; padding:32px; color:#1a1410;">
      <div style="max-width:520px; margin:0 auto; background:#ffffff; border:1px solid #e8dfd1; border-radius:16px; padding:32px;">
        <h1 style="font-size:22px; margin:0 0 8px; color:#1a1410;">Essential Gemstones \u00b7 Admin sign-in</h1>
        <p style="color:#5a4a3d; font-size:14px; margin:0 0 24px;">Hi {username}, use this code to finish signing in. It expires in {EMAIL_OTP_TTL_MINUTES} minutes.</p>
        <div style="font-family: 'Courier New', monospace; font-size:34px; letter-spacing:12px; text-align:center; padding:20px; background:#faf6f0; border:1px solid #e8dfd1; border-radius:12px; color:#1a1410;">
          {code}
        </div>
        <p style="color:#8b6b4f; font-size:12px; margin:24px 0 0;">If you didn\u2019t try to sign in, you can safely ignore this email \u2014 no one can get in without your password.</p>
      </div>
    </div>
    """


async def _store_email_otp(admin_id: str, code: str, coll: Any = None) -> None:
    coll = coll if coll is not None else db.admin_email_otps
    await coll.update_one(
        {"_id": admin_id},
        {
            "$set": {
                "code_hash": hash_password(code),
                "expires_at": (datetime.utcnow() + timedelta(minutes=EMAIL_OTP_TTL_MINUTES)).isoformat(),
                "sent_at": datetime.utcnow().isoformat(),
                "attempts": 0,
            }
        },
        upsert=True,
    )


async def _consume_email_otp(admin_id: str, code: str, coll: Any = None) -> bool:
    coll = coll if coll is not None else db.admin_email_otps
    row = await coll.find_one({"_id": admin_id})
    if not row:
        return False
    try:
        expires = datetime.fromisoformat(row.get("expires_at"))
    except Exception:
        return False
    if datetime.utcnow() > expires:
        await coll.delete_one({"_id": admin_id})
        return False
    if int(row.get("attempts", 0)) >= EMAIL_OTP_MAX_ATTEMPTS:
        await coll.delete_one({"_id": admin_id})
        return False
    clean = (code or "").strip()
    if not clean.isdigit() or len(clean) != 6:
        await coll.update_one({"_id": admin_id}, {"$inc": {"attempts": 1}})
        return False
    if not verify_password(clean, row.get("code_hash", "")):
        await coll.update_one({"_id": admin_id}, {"$inc": {"attempts": 1}})
        return False
    # success: burn the code
    await coll.delete_one({"_id": admin_id})
    return True


async def _otp_resend_wait(coll: Any, key: str) -> int:
    prev = await coll.find_one({"_id": key})
    if not prev or not prev.get("sent_at"):
        return 0
    try:
        last = datetime.fromisoformat(prev["sent_at"])
    except Exception:
        return 0
    return max(0, EMAIL_OTP_RESEND_SECONDS - int((datetime.utcnow() - last).total_seconds()))


# ---------- Trusted-Device tokens (30-day "skip 2FA on this device") ---------- #

TRUSTED_DEVICE_DAYS = 30


def _make_trusted_device_token(admin_id: str, jti: str) -> str:
    payload = {
        "sub": admin_id,
        "jti": jti,
        "purpose": "trusted_device",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=TRUSTED_DEVICE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _decode_trusted_device_token(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "trusted_device":
        return None
    return payload


async def _issue_trusted_device(admin_id: str, user_agent: str) -> str:
    jti = str(uuid.uuid4())
    await db.admin_trusted_devices.insert_one(
        {
            "_id": jti,
            "adminId": admin_id,
            "userAgent": (user_agent or "")[:255],
            "createdAt": datetime.utcnow().isoformat(),
            "lastUsedAt": datetime.utcnow().isoformat(),
            "expiresAt": (datetime.utcnow() + timedelta(days=TRUSTED_DEVICE_DAYS)).isoformat(),
        }
    )
    return _make_trusted_device_token(admin_id, jti)


async def _check_trusted_device(admin_id: str, token: str) -> bool:
    payload = _decode_trusted_device_token(token)
    if not payload or payload.get("sub") != admin_id:
        return False
    row = await db.admin_trusted_devices.find_one({"_id": payload.get("jti"), "adminId": admin_id})
    if not row:
        return False
    # DB row expiry check (JWT also has exp, but this lets admins revoke)
    try:
        expires = datetime.fromisoformat(row.get("expiresAt"))
    except Exception:
        return False
    if datetime.utcnow() > expires:
        await db.admin_trusted_devices.delete_one({"_id": row["_id"]})
        return False
    # touch last-used timestamp (best effort)
    await db.admin_trusted_devices.update_one(
        {"_id": row["_id"]}, {"$set": {"lastUsedAt": datetime.utcnow().isoformat()}}
    )
    return True


def make_token(sub: str, is_super: bool, permissions: list[str], username: str, role: str = "admin") -> str:
    payload = {
        "sub": sub,
        "username": username,
        "role": role,
        "isSuper": is_super,
        "permissions": permissions,
        "purpose": "full",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=JWT_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def make_2fa_challenge_token(admin_id: str, username: str) -> str:
    payload = {
        "sub": admin_id,
        "username": username,
        "role": "admin",
        "purpose": "verify2fa",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(minutes=TWO_FA_CHALLENGE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def make_2fa_setup_token(admin_id: str, username: str) -> str:
    payload = {
        "sub": admin_id,
        "username": username,
        "role": "admin",
        "purpose": "setup2fa",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(minutes=SETUP_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def make_user_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "user",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=JWT_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _decode_token(creds: Optional[HTTPAuthorizationCredentials]) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


async def require_admin(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    payload = _decode_token(creds)
    # Reject explicit user tokens; legacy admin tokens without role are still accepted.
    if payload.get("role") == "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an admin token")
    # Only full-purpose admin tokens can access general admin endpoints.
    purpose = payload.get("purpose")
    if purpose and purpose != "full":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session is limited to 2FA setup. Finish enrollment first.",
        )
    return payload


async def require_setup_2fa(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    payload = _decode_token(creds)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Admin token required")
    if payload.get("purpose") not in ("setup2fa", "full"):
        raise HTTPException(status_code=401, detail="This session cannot enroll 2FA")
    return payload


async def require_challenge_2fa(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    payload = _decode_token(creds)
    if payload.get("role") != "admin" or payload.get("purpose") != "verify2fa":
        raise HTTPException(status_code=401, detail="Invalid 2FA challenge token")
    return payload


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    payload = _decode_token(creds)
    if payload.get("role") != "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User token required")
    # Verify user still exists and is not banned
    doc = await db.users.find_one({"_id": payload["sub"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    if doc.get("isBanned"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has been suspended.")
    return payload


def require_super(payload: dict) -> None:
    if not payload.get("isSuper"):
        raise HTTPException(status_code=403, detail="Super admin only")


def doc_to_admin(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "username": doc["username"],
        "email": doc.get("email"),
        "permissions": doc.get("permissions", []),
        "isSuper": bool(doc.get("isSuper")),
        "twoFactorEnabled": bool(doc.get("twoFactorEnabled")),
        "phone": _mask_phone(doc.get("phone") or "") or None,
        "createdAt": doc.get("createdAt"),
    }


# ---------------- DEFAULT SITE CONTENT ---------------- #


def default_site() -> dict:
    return {
        "navbar": {
            "brand": "Essential Gemstones",
            "links": [
                {"label": "Shop", "href": "#shop"},
                {"label": "Our Story", "href": "#story"},
                {"label": "Chakra Guide", "href": "#chakra"},
                {"label": "Founder", "href": "#founder"},
                {"label": "FAQ", "href": "#faq"},
                {"label": "Contact", "href": "#contact"},
            ],
            "ctaLabel": "Shop Now",
            "ctaHref": "#shop",
        },
        "hero": {
            "kicker": "Handmade \u00b7 Volcanic \u00b7 Intentional",
            "titleLine1": "Essential",
            "titleLine2": "Gemstones",
            "subtitle": "Handmade lava stone bracelets inspired by nature and strength. Born from fire, shaped by hand \u2014 each piece carries a quiet story you can wear.",
            "ctaPrimary": {"label": "Shop the Collection", "href": "#shop"},
            "ctaSecondary": {"label": "Our Story", "href": "#story"},
            "mediaType": "image",
            "mediaUrl": "https://images.unsplash.com/photo-1509222923806-0ef1ff755ab6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODh8MHwxfHNlYXJjaHwzfHx2b2xjYW5pYyUyMHN0b25lfGVufDB8fHx8MTc4MTczMjgzNXww&ixlib=rb-4.1.0&q=85",
            "quoteText": "What we wear can carry meaning.",
            "quoteAuthor": "\u2014 LUCA, FOUNDER",
        },
        "products": {
            "kicker": "Shop Our Latest Creations",
            "title": "The Collection",
            "subtitle": "Discover our unique selection of handcrafted lava stone bracelets. Each piece is designed to bring natural beauty and strength to your daily life.",
            "items": [
                {"id": "cross-faith", "name": "Cross of Faith Lava Stone Bracelet", "price": "$24.00", "image": "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/width:2000/https://cdn.gamma.app/e4xhbiak5gqtkn6/169bc339a348442090f43887e3989cac/original/Lava_Christian_Cross_Silver.jpg", "description": "Handcrafted lava stone bracelet featuring a silver cross \u2014 a quiet symbol of faith you can carry with you every day.", "buyUrl": "https://buy.stripe.com/dRm4gse2veRk3RZd15gYU00", "badge": "New"},
                {"id": "chakra", "name": "7 Chakra Lava Stone Bracelet", "price": "$28.00", "image": "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/width:2000/https://cdn.gamma.app/e4xhbiak5gqtkn6/70ec7e9cde304cbe90a6029669423444/original/7-Chakra-Healing-Beaded-Bracelet-Natural-Lava-Stone-Diffuser-Bracelet-Jewelry.jpg", "description": "Seven sacred stones aligned with the chakras, paired with porous lava beads ready to diffuse your favorite oils.", "buyUrl": "https://buy.stripe.com/fZufZa1fJcJcdsz9OTgYU02", "badge": "New"},
            ],
        },
        "story": {
            "kicker": "Our Story",
            "title": "Born from the Earth, Made by Hand",
            "image": "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/width:2000/https://cdn.gamma.app/e4xhbiak5gqtkn6/3380d4a8244a4e7393e45cd0b281d33a/original/7-Chakra-Healing-Beaded-Bracelet-Natural-Lava-Stone-Diffuser-Bracelet-Jewelry-1.jpg",
            "badge": "One bracelet at a time.",
            "paragraphs": [
                "Essential Gemstones was born from a deep reverence for the natural world \u2014 its raw textures, ancient rhythms, and quiet power. Founded by Luca, this small, intentional brand exists at the intersection of craftsmanship and crystal energy.",
                "Every bracelet begins as a vision and ends as something you can feel against your skin \u2014 grounding, warm, and alive. No mass production. No shortcuts. Just thoughtful, handcrafted jewelry made one bracelet at a time.",
                "Lava stone \u2014 the cornerstone of every Essential Gemstones design \u2014 is one of the oldest and most powerful stones on earth. Formed in fire and shaped by nature over thousands of years, it carries the energy of transformation, grounding, and raw strength.",
            ],
        },
        "promise": {"kicker": "Our Promise", "title": "Why Choose Essential Gemstones?", "body": "We want your bracelet to be a cherished companion for years to come. That\u2019s why every Essential Gemstones package includes extra beads and a sturdy elastic band \u2014 your beloved piece is fully restringable, empowering you to easily repair or customize it yourself, right at home."},
        "chakra": {
            "kicker": "Our Craft",
            "title": "Awaken Your Spirit: The 7 Chakra Bracelet",
            "subtitle": "Embrace balance and harmony with our handcrafted 7 Chakra Lava Stone Bracelet. Each stone is carefully selected to align with your energy centers, while lava stone beads offer a unique way to diffuse essential oils.",
            "footer": "Each stone works in harmony, aligning your chakras from root to crown. Simply add a drop of your favorite essential oil to the lava beads for an aromatic experience that complements your journey.",
            "stones": [
                {"stone": "Red Jasper", "chakra": "Root Chakra", "color": "#a8473d", "desc": "Feel grounded and stable with Red Jasper, anchoring your spirit to the Earth. It brings strength and fosters a sense of security."},
                {"stone": "Tiger's Eye", "chakra": "Sacral / Solar Plexus", "color": "#b07a3a", "desc": "Ignite your inner fire with Tiger\u2019s Eye, boosting confidence, courage, and personal power to pursue your true desires."},
                {"stone": "Stone Amplifier", "chakra": "Solar Plexus", "color": "#d4a85a", "desc": "Our special resin bead radiates warmth, harmonizing and amplifying the healing energies of all surrounding crystals."},
                {"stone": "Serpentine", "chakra": "Heart Chakra", "color": "#5e7a4a", "desc": "Open your heart to healing and renewal. Serpentine connects you to nature\u2019s nurturing energy, fostering peace and compassion."},
                {"stone": "Turquoise", "chakra": "Throat Chakra", "color": "#3a8a96", "desc": "Speak your truth with clarity and calm. Turquoise empowers honest communication and brings a tranquil presence."},
                {"stone": "Lapis Lazuli", "chakra": "Third Eye Chakra", "color": "#2b4a8c", "desc": "Awaken your intuition and inner wisdom. Lapis Lazuli deepens clarity and insight, guiding you towards profound understanding."},
                {"stone": "Amethyst", "chakra": "Crown Chakra", "color": "#7a4f9c", "desc": "Connect to higher consciousness and spiritual protection. Amethyst brings peace, purifying your aura and elevating your connection."},
            ],
        },
        "stats": {
            "kicker": "Best Sellers",
            "title": "Why Customers Love Us",
            "items": [
                {"number": "100%", "label": "Handmade", "sub": "Every bracelet assembled by hand, one at a time, with full intention."},
                {"number": "100+", "label": "Happy Customers", "sub": "A growing community of wearers who carry a piece of the earth daily."},
                {"number": "5.0\u2605", "label": "Rating", "sub": "Consistently loved for quality, beauty, and meaningful craftsmanship."},
                {"number": "2", "label": "Unique Designs", "sub": "From minimalist earth tones to bold gemstone pairings \u2014 a bracelet for every spirit."},
            ],
        },
        "lavaMeaning": {
            "kicker": "The Power Within",
            "title": "What Lava Stone Means",
            "subtitle": "More than a material \u2014 lava stone is a symbol, a history, and an energy all its own.",
            "items": [
                {"title": "Strength & Grounding", "icon": "Mountain", "desc": "Lava stone is formed under immense pressure and heat deep within the earth. That origin story translates into a powerful grounding energy \u2014 helping you stay rooted, calm, and centered."},
                {"title": "Transformation", "icon": "Flame", "desc": "Few symbols are more powerful than lava cooling into solid stone. It represents profound transformation \u2014 the ability to move through fire and emerge stronger, more defined, and beautifully new."},
                {"title": "Connection to Nature", "icon": "Leaf", "desc": "Lava stone is one of the most natural materials you can wear. Porous, earthy, and deeply textured, it carries the memory of ancient forests and volcanic coastlines."},
                {"title": "Protection & Courage", "icon": "Shield", "desc": "Throughout cultures and centuries, volcanic stone has been revered as a protective talisman. Many believe it absorbs negative energy and fortifies the spirit."},
            ],
        },
        "founder": {
            "kicker": "Meet the Founder",
            "title": "Hi, I\u2019m Luca",
            "image": "https://images.unsplash.com/photo-1632670549453-7a3dfac254a2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwyfHxiZWFkZWQlMjBicmFjZWxldHxlbnwwfHx8fDE3ODE3MzI4MzV8MA&ixlib=rb-4.1.0&q=85",
            "ageBadge": "9",
            "ageLabel": "Year Old Founder",
            "intro": "I\u2019m a nine-year-old entrepreneur, and the founder of Essential Gemstones. I love bringing the magic of natural stones to life by creating special, meaningful pieces for you.",
            "blocks": [
                {"icon": "Sparkles", "title": "Why I Love Gemstones", "desc": "For me, gemstones and crystals are simply amazing. Each one has its own vibrant color, unique energy, and a fascinating story."},
                {"icon": "Lightbulb", "title": "How It Started", "desc": "Gemstones always felt magical to me, and I wanted to share that feeling with everyone. I hand-pick every stone with purpose and design each piece with care."},
                {"icon": "Heart", "title": "My Promise to You", "desc": "Even though I\u2019m young, I take my business very seriously. Essential Gemstones is my dream, and I\u2019m incredibly proud of every bracelet I make."},
            ],
        },
        "craft": {
            "kicker": "Craftsmanship",
            "title": "What Goes Into Every Bracelet",
            "subtitle": "From material selection to final packaging, every step is approached with care and quality.",
            "image": "https://images.unsplash.com/photo-1609619742069-f5e18afeef17?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwzfHxqZXdlbHJ5JTIwbWFraW5nfGVufDB8fHx8MTc4MTczMjgzNXww&ixlib=rb-4.1.0&q=85",
            "steps": [
                {"number": "01", "title": "Premium Natural Materials", "desc": "Every bracelet begins with genuine lava stone sourced for its texture, porosity, and energy. Paired stones \u2014 amethysts, turquoise and more \u2014 are hand-selected for quality and color harmony."},
                {"number": "02", "title": "Thoughtful Design", "desc": "Each design is developed with a specific intention \u2014 grounding, protection, clarity, love. Bead combinations, sizing, and accent choices are deliberate, not accidental."},
                {"number": "03", "title": "Handcrafted Assembly", "desc": "Each bracelet is made by hand using durable, stretch-resistant elastic and secure finishing techniques. The result is a piece that is beautiful and built to last."},
            ],
        },
        "faq": {
            "kicker": "FAQ",
            "title": "Frequently Asked Questions",
            "subtitle": "Everything you need to know before your first \u2014 or next \u2014 order.",
            "items": [
                {"q": "How do I care for my lava stone bracelet?", "a": "Lava stone is naturally porous and durable, but a little care goes a long way. Avoid prolonged exposure to water or harsh chemicals. To clean, simply wipe with a soft, slightly damp cloth and let air dry. Store in the pouch provided to prevent scratching from other jewelry."},
                {"q": "Can I add essential oils to my lava stone bracelet?", "a": "Absolutely \u2014 in fact, it\u2019s one of the most beloved features of lava stone. Because the stone is porous, it naturally absorbs and diffuses essential oils throughout the day. Simply place 1\u20132 drops of your chosen oil on the lava beads, allow a moment to absorb, and enjoy hours of subtle, natural aromatherapy."},
                {"q": "How long does shipping take?", "a": "Standard orders are typically handcrafted and shipped within 2\u20133 business days. Domestic delivery takes an additional 3\u20135 business days. We offer tracked shipping on all orders."},
                {"q": "Do you accept returns or exchanges?", "a": "We want you to love your bracelet. If something isn\u2019t right, reach out within 30 days of delivery and we\u2019ll do our best to make it right."},
            ],
        },
        "gallery": {
            "kicker": "Gallery",
            "title": "A Closer Look at Our Craft",
            "images": [
                "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/height:400/https://cdn.gamma.app/e4xhbiak5gqtkn6/387d1923497d418ba2f394eaa42fe17d/original/d08456c0-ead8-41da-8e65-b2cc763935e8.jpg",
                "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/height:400/https://cdn.gamma.app/e4xhbiak5gqtkn6/147b5b49684d4a42aa23fcd65c03198d/original/70d0daee-d92d-469b-8efb-b6cba87da969.jpg",
                "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/height:400/https://cdn.gamma.app/e4xhbiak5gqtkn6/29f372cabe39493d94b4e330d9aa6835/original/99e9cc1d-3c06-4647-a475-3184d5dfae86.jpg",
                "https://imgproxy.gamma.app/resize/quality:80/resizing_type:fit/height:400/https://cdn.gamma.app/e4xhbiak5gqtkn6/742c8de3a3c5488fb7cd904aa892f1b2/original/3fd64ee4-cd43-4cac-920e-378cde876b3a.jpg",
            ],
        },
        "vip": {
            "kicker": "Exclusive Access",
            "title": "Join our VIP Membership",
            "subtitle": "Unlock a world of unique benefits, members-only discounts, and special content from Luca. Become part of our inner circle today.",
            "perks": [
                {"icon": "Gift", "label": "Members-only discounts"},
                {"icon": "Star", "label": "Early access to drops"},
                {"icon": "MessageCircle", "label": "Stories from the studio"},
            ],
            "ctaLabel": "Join the VIP Club",
            "ctaUrl": "https://buy.stripe.com/eVqeV65vZeRkcov5yDgYU03",
            "memberKicker": "Members Only",
            "memberGreeting": "Welcome, {name}.",
            "memberIntro": "You\u2019re officially part of Luca\u2019s inner circle. Here\u2019s what you unlock as a member:",
            "memberPerks": [
                {"icon": "Star", "title": "Member code", "desc": "**FAMILY10** \u2014 10% off your next order."},
                {"icon": "Gift", "title": "Early access", "desc": "48 hours before public release on new drops."},
                {"icon": "Heart", "title": "Free re-stringing", "desc": "On any Essential Gemstones bracelet, once a year."},
                {"icon": "MessageCircle", "title": "Studio stories", "desc": "Behind-the-scenes updates straight from Luca."},
            ],
            "lockedKicker": "Sign up to unlock",
            "lockedTitle": "Exclusive member perks",
            "lockedText": "Discount code, early access to new drops, free bracelet re-stringing, and studio stories \u2014 free with your Essential Gemstones account.",
            "lockedCtaLabel": "Join free",
        },
        "footer": {
            "brand": "Essential Gemstones",
            "tagline": "Join our growing community of crystal lovers, nature seekers, and everyday wearers. Be the first to know about new collections, restocks, and stories from the studio.",
            "newsletterKicker": "Stay Connected",
            "newsletterTitle": "Get the latest from the studio.",
            "email": "Essentialgemstones@googlegroups.com",
            "contactEmail": "luca@essentialgemstones.com",
            "contactSubject": "Contact Essential Gemstones",
            "donateTitle": "Support Luca\u2019s Dream",
            "donateText": "Every donation \u2014 big or small \u2014 helps keep Essential Gemstones growing.",
            "donateUrl": "https://donate.stripe.com/00w14g5vZfVo88f2mrgYU01",
            "donateLabel": "Donate Now",
            "copyright": "Handmade with intention.",
            "quote": "\u201cThank you from the bottom of my heart.\u201d \u2014 Luca",
            "socials": {"instagram": "#", "facebook": "#"},
        },
        "sectionOrder": ["hero", "products", "story", "promise", "chakra", "stats", "lavaMeaning", "founder", "craft", "faq", "gallery", "vip"],
        "sectionVisibility": {k: True for k in ["hero", "products", "story", "promise", "chakra", "stats", "lavaMeaning", "founder", "craft", "faq", "gallery", "vip"]},
    }


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


async def get_site_doc() -> dict:
    doc = await db.site.find_one({"_id": "main"})
    if doc is None:
        doc = {"_id": "main", **default_site()}
        await db.site.insert_one(doc)
    doc.pop("_id", None)
    # Fill any missing keys from defaults so partial saves can never blank out a section
    return _deep_merge(default_site(), doc)


# ---------------- ROUTES ---------------- #


@app.get("/api/")
async def root() -> dict:
    return {"message": "Essential Gemstones API"}


@app.post("/api/admin/login")
async def admin_login(data: LoginIn, request: Request) -> dict:
    # Master password shortcut is removed. All logins go through the admins collection.
    if not data.username or not data.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    attempt_key = await check_password_attempt(db, "admin", data.username)
    doc = await db.admins.find_one({"username": data.username.lower().strip()})
    if not doc or not verify_password(data.password, doc.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await db.password_attempts.delete_one({"_id": attempt_key})

    if doc.get("twoFactorEnabled"):
        # If the browser presents a valid trusted-device token for this admin, skip 2FA.
        trust_token = request.headers.get("X-Admin-Trust-Token", "").strip()
        if trust_token and await _check_trusted_device(doc["_id"], trust_token):
            token = make_token(
                sub=doc["_id"],
                is_super=bool(doc.get("isSuper")),
                permissions=doc.get("permissions", []),
                username=doc["username"],
            )
            return {"status": "ok", "token": token, "user": doc_to_admin(doc), "trustedDevice": True}

        # Otherwise, return a short-lived 2FA challenge token.
        return {
            "status": "needs_2fa",
            "twoFactorToken": make_2fa_challenge_token(doc["_id"], doc["username"]),
            "username": doc["username"],
            "availableMethods": _available_2fa_methods(doc),
            "emailHint": _obfuscate_email(doc.get("email") or "") if doc.get("email") else None,
            "phoneHint": _mask_phone(doc.get("phone") or "") or None,
        }

    # 2FA not yet enrolled — issue a setup-only token so the admin must enroll before doing anything.
    return {
        "status": "needs_2fa_setup",
        "setupToken": make_2fa_setup_token(doc["_id"], doc["username"]),
        "user": doc_to_admin(doc),
    }


# ---- 2FA ENDPOINTS ---- #


class TwoFactorVerifyIn(BaseModel):
    code: str


class TwoFactorLoginIn(BaseModel):
    code: str
    method: Optional[str] = None  # "totp" | "email" | "backup" (auto-detect if missing)
    trustDevice: Optional[bool] = False


def _available_2fa_methods(doc: dict) -> list[str]:
    methods = ["totp"]
    if (doc.get("email") or "").strip():
        methods.append("email")
    if (doc.get("phone") or "").strip() and doc.get("phoneVerifiedAt"):
        methods.append("sms")
    return methods


@app.post("/api/admin/2fa/setup")
async def admin_2fa_setup(admin: dict = Depends(require_setup_2fa)) -> dict:
    """Generate (or return existing pending) TOTP secret + provisioning QR code."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    # If 2FA is already enabled, don't hand out the current secret.
    if doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is already enabled for this admin.")

    secret = doc.get("twoFactorPendingSecret") or _new_totp_secret()
    if not doc.get("twoFactorPendingSecret"):
        await db.admins.update_one({"_id": doc["_id"]}, {"$set": {"twoFactorPendingSecret": secret}})

    uri = _totp_provisioning_uri(f"{TOTP_ISSUER}:{doc['username']}", secret)
    qr = _totp_qr_data_url(uri)
    return {
        "secret": secret,
        "provisioningUri": uri,
        "qrDataUrl": qr,
        "issuer": TOTP_ISSUER,
        "accountName": doc["username"],
        "digits": 6,
        "period": 30,
        "algorithm": "SHA1",
    }


@app.post("/api/admin/2fa/enable")
async def admin_2fa_enable(payload: TwoFactorVerifyIn, admin: dict = Depends(require_setup_2fa)) -> dict:
    """Verify the first 6-digit code from the authenticator app, then enable 2FA and issue a full session."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    if doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is already enabled.")
    secret = doc.get("twoFactorPendingSecret")
    if not secret:
        raise HTTPException(status_code=400, detail="Call /api/admin/2fa/setup first.")
    if not _verify_totp(secret, payload.code):
        raise HTTPException(status_code=401, detail="Invalid code. Try the current 6-digit code from your authenticator.")

    backup_codes = _new_backup_codes()
    hashed_backups = _hash_backup_codes(backup_codes)
    await db.admins.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "twoFactorSecret": secret,
                "twoFactorEnabled": True,
                "twoFactorBackupCodes": hashed_backups,
                "twoFactorEnabledAt": datetime.utcnow().isoformat(),
            },
            "$unset": {"twoFactorPendingSecret": ""},
        },
    )
    fresh = await db.admins.find_one({"_id": doc["_id"]})
    token = make_token(
        sub=fresh["_id"],
        is_super=bool(fresh.get("isSuper")),
        permissions=fresh.get("permissions", []),
        username=fresh["username"],
    )
    return {
        "ok": True,
        "backupCodes": backup_codes,
        "token": token,
        "user": doc_to_admin(fresh),
    }


@app.post("/api/admin/2fa/login")
async def admin_2fa_login(payload: TwoFactorLoginIn, request: Request, admin: dict = Depends(require_challenge_2fa)) -> dict:
    """Second step of login: verify TOTP / email OTP / backup code, and return the real admin JWT."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc or not doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled for this admin.")
    code = (payload.code or "").strip()
    method = (payload.method or "").strip().lower()
    secret = doc.get("twoFactorSecret") or ""

    verified = False
    if method == "email":
        verified = await _consume_email_otp(doc["_id"], code)
    elif method == "sms":
        verified = bool(doc.get("phoneVerifiedAt") and doc.get("phone") and await consume_sms_code(db.admin_sms_otps, doc["_id"], code, _normalize_phone(doc["phone"])))
    elif method == "backup":
        idx = _match_backup_code(code, doc.get("twoFactorBackupCodes") or [])
        if idx >= 0:
            remaining = list(doc.get("twoFactorBackupCodes") or [])
            remaining.pop(idx)
            await db.admins.update_one({"_id": doc["_id"]}, {"$set": {"twoFactorBackupCodes": remaining}})
            verified = True
    elif method == "totp":
        verified = _verify_totp(secret, code)
    else:
        # Auto-detect (backwards compatibility): try TOTP -> email OTP (only if one is pending) -> backup code
        if _verify_totp(secret, code):
            verified = True
        else:
            has_pending_email_otp = await db.admin_email_otps.find_one({"_id": doc["_id"]}) is not None
            has_pending_sms_otp = await db.admin_sms_otps.find_one({"_id": doc["_id"]}) is not None
            if has_pending_email_otp and await _consume_email_otp(doc["_id"], code):
                verified = True
            elif has_pending_sms_otp and doc.get("phoneVerifiedAt") and doc.get("phone") and await consume_sms_code(db.admin_sms_otps, doc["_id"], code, _normalize_phone(doc["phone"])):
                verified = True
            else:
                idx = _match_backup_code(code, doc.get("twoFactorBackupCodes") or [])
                if idx >= 0:
                    remaining = list(doc.get("twoFactorBackupCodes") or [])
                    remaining.pop(idx)
                    await db.admins.update_one({"_id": doc["_id"]}, {"$set": {"twoFactorBackupCodes": remaining}})
                    verified = True

    if not verified:
        raise HTTPException(status_code=401, detail="Invalid code")

    token = make_token(
        sub=doc["_id"],
        is_super=bool(doc.get("isSuper")),
        permissions=doc.get("permissions", []),
        username=doc["username"],
    )
    resp: dict = {"ok": True, "token": token, "user": doc_to_admin(doc)}
    if payload.trustDevice:
        ua = request.headers.get("User-Agent", "")
        resp["trustDeviceToken"] = await _issue_trusted_device(doc["_id"], ua)
        resp["trustDeviceDays"] = TRUSTED_DEVICE_DAYS
    return resp


class TwoFAChallengeIn(BaseModel):
    twoFactorToken: str


@app.post("/api/admin/2fa/email/send")
async def admin_2fa_email_send(admin: dict = Depends(require_challenge_2fa)) -> dict:
    """Send a one-time 6-digit code to the admin's email as an alternative to the authenticator app."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc or not doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled for this admin.")
    email = (doc.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="No email is set for this admin. Ask a super admin to add one, or use your authenticator app.")

    # Rate-limit: 30 s between resends
    prev = await db.admin_email_otps.find_one({"_id": doc["_id"]})
    if prev and prev.get("sent_at"):
        try:
            last = datetime.fromisoformat(prev["sent_at"])
            wait = EMAIL_OTP_RESEND_SECONDS - int((datetime.utcnow() - last).total_seconds())
            if wait > 0:
                raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another code.")
        except HTTPException:
            raise
        except Exception:
            pass

    if not SMTP_USER or not SMTP_PASS:
        raise HTTPException(status_code=500, detail="Email 2FA isn\u2019t available on this server (SMTP not configured). Use your authenticator app.")

    code = _new_email_otp()
    await _store_email_otp(doc["_id"], code)
    try:
        await send_email(email, "Your Essential Gemstones admin code", _email_otp_html(doc.get("username", "there"), code))
    except Exception as e:
        logging.exception("Failed to send admin 2FA email OTP")
        raise HTTPException(status_code=502, detail=f"Couldn\u2019t send the email: {e}")

    return {
        "ok": True,
        "sentTo": _obfuscate_email(email),
        "expiresInMinutes": EMAIL_OTP_TTL_MINUTES,
        "resendAfterSeconds": EMAIL_OTP_RESEND_SECONDS,
    }


@app.get("/api/admin/2fa/methods")
async def admin_2fa_methods(admin: dict = Depends(require_challenge_2fa)) -> dict:
    """List the 2FA methods available for the admin whose password was just verified."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    methods = _available_2fa_methods(doc)
    return {
        "methods": methods,
        "emailHint": _obfuscate_email(doc.get("email") or "") if doc.get("email") else None,
        "phoneHint": _mask_phone(doc.get("phone") or "") or None,
        "hasBackupCodes": bool(doc.get("twoFactorBackupCodes")),
    }


@app.post("/api/admin/2fa/sms/send", response_model=PhoneCodeResponse)
async def admin_2fa_sms_send(admin: dict = Depends(require_challenge_2fa)) -> dict:
    """Text a one-time code to the admin's verified number through Twilio."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc or not doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled for this admin.")
    phone = doc.get("phone") or ""
    if not phone or not doc.get("phoneVerifiedAt"):
        raise HTTPException(status_code=400, detail="No verified phone on this admin account. Add one in the dashboard, or use another method.")
    return await send_sms_code(db, db.admin_sms_otps, doc["_id"], _normalize_phone(phone), "admin sign-in")


# ---- Admin phone (self-service, verified by SMS) ---- #


class AdminPhoneIn(BaseModel):
    phone: str


@app.put("/api/admin/me/phone", response_model=PhoneCodeResponse)
async def admin_set_phone(payload: AdminPhoneIn, admin: dict = Depends(require_admin)) -> dict:
    """Start adding a phone: store as pending and text a verification code."""
    phone = _normalize_phone(payload.phone)
    return await send_sms_code(db, db.admin_phone_verify, admin["sub"], phone, "phone verification")


@app.post("/api/admin/me/phone/verify")
async def admin_verify_phone(payload: TwoFactorVerifyIn, admin: dict = Depends(require_admin)) -> dict:
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found.")
    verified = await consume_sms_code(db.admin_phone_verify, admin["sub"], payload.code)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid or expired code.")
    await db.admins.update_one(
        {"_id": admin["sub"]},
        {
            "$set": {"phone": verified["phone"], "phoneVerifiedAt": datetime.now(timezone.utc).isoformat()},
            "$unset": {"phoneCarrier": "", "pendingPhone": "", "pendingPhoneCarrier": ""},
        },
    )
    await db.admin_sms_otps.delete_one({"_id": admin["sub"]})
    fresh = await db.admins.find_one({"_id": admin["sub"]})
    return {"ok": True, "user": doc_to_admin(fresh)}


@app.delete("/api/admin/me/phone")
async def admin_remove_phone(admin: dict = Depends(require_admin)) -> dict:
    await revoke_admin_codes(db, admin["sub"])
    await db.admins.update_one(
        {"_id": admin["sub"]},
        {"$unset": {"phone": "", "phoneCarrier": "", "phoneVerifiedAt": "", "pendingPhone": "", "pendingPhoneCarrier": ""}},
    )
    fresh = await db.admins.find_one({"_id": admin["sub"]})
    return {"ok": True, "user": doc_to_admin(fresh)}


# ---- Trusted device management ---- #


@app.get("/api/admin/trusted-devices")
async def list_trusted_devices(admin: dict = Depends(require_admin)) -> list[dict]:
    cursor = db.admin_trusted_devices.find({"adminId": admin.get("sub")})
    out: list[dict] = []
    async for row in cursor:
        out.append(
            {
                "id": row.get("_id"),
                "userAgent": row.get("userAgent"),
                "createdAt": row.get("createdAt"),
                "lastUsedAt": row.get("lastUsedAt"),
                "expiresAt": row.get("expiresAt"),
            }
        )
    return out


@app.delete("/api/admin/trusted-devices/{device_id}")
async def revoke_trusted_device(device_id: str, admin: dict = Depends(require_admin)) -> dict:
    res = await db.admin_trusted_devices.delete_one({"_id": device_id, "adminId": admin.get("sub")})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trusted device not found")
    return {"ok": True}


@app.delete("/api/admin/trusted-devices")
async def revoke_all_trusted_devices(admin: dict = Depends(require_admin)) -> dict:
    res = await db.admin_trusted_devices.delete_many({"adminId": admin.get("sub")})
    return {"ok": True, "revoked": res.deleted_count}


@app.post("/api/admin/2fa/disable")
async def admin_2fa_disable(payload: TwoFactorVerifyIn, admin: dict = Depends(require_admin)) -> dict:
    """Disable 2FA on your OWN admin account (requires current 6-digit code)."""
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled.")
    if not _verify_totp(doc.get("twoFactorSecret") or "", payload.code):
        raise HTTPException(status_code=401, detail="Invalid code")
    await db.admins.update_one(
        {"_id": doc["_id"]},
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
    # Revoke all trusted devices tied to this admin
    await db.admin_trusted_devices.delete_many({"adminId": doc["_id"]})
    await db.admin_email_otps.delete_one({"_id": doc["_id"]})
    await revoke_admin_codes(db, doc["_id"])
    return {"ok": True}


@app.get("/api/admin/2fa/backup-codes")
async def admin_2fa_backup_codes_remaining(admin: dict = Depends(require_admin)) -> dict:
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {
        "enabled": bool(doc.get("twoFactorEnabled")),
        "remaining": len(doc.get("twoFactorBackupCodes") or []),
    }


@app.post("/api/admin/2fa/backup-codes/regenerate")
async def admin_2fa_regenerate_backup_codes(payload: TwoFactorVerifyIn, admin: dict = Depends(require_admin)) -> dict:
    doc = await db.admins.find_one({"_id": admin["sub"]})
    if not doc or not doc.get("twoFactorEnabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled.")
    if not _verify_totp(doc.get("twoFactorSecret") or "", payload.code):
        raise HTTPException(status_code=401, detail="Invalid code")
    codes = _new_backup_codes()
    await db.admins.update_one(
        {"_id": doc["_id"]},
        {"$set": {"twoFactorBackupCodes": _hash_backup_codes(codes)}},
    )
    return {"backupCodes": codes}


@app.post("/api/admin/2fa/reset/{admin_id}")
async def admin_2fa_reset(admin_id: str, admin: dict = Depends(require_admin)) -> dict:
    """Super-admin only: wipe another admin's 2FA (so they can re-enroll on next login)."""
    require_super(admin)
    doc = await db.admins.find_one({"_id": admin_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.admins.update_one(
        {"_id": admin_id},
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
    await db.admin_trusted_devices.delete_many({"adminId": admin_id})
    await db.admin_email_otps.delete_one({"_id": admin_id})
    await revoke_admin_codes(db, admin_id)
    return {"ok": True}


@app.get("/api/admin/me")
async def admin_me(admin: dict = Depends(require_admin)) -> dict:
    doc = await db.admins.find_one({"_id": admin.get("sub")})
    if doc:
        return {"ok": True, "user": doc_to_admin(doc)}
    return {
        "ok": True,
        "user": {
            "id": admin.get("sub"),
            "username": admin.get("username"),
            "isSuper": bool(admin.get("isSuper")),
            "permissions": admin.get("permissions", []),
            "twoFactorEnabled": False,
        },
    }


# ---- admin user management (super only) ---- #


@app.get("/api/admin/admins")
async def list_admins(admin: dict = Depends(require_admin)) -> list[dict]:
    require_super(admin)
    cursor = db.admins.find({}, {"passwordHash": 0})
    out: list[dict] = []
    async for doc in cursor:
        out.append(doc_to_admin(doc))
    return out


@app.post("/api/admin/admins")
async def create_admin(payload: AdminCreate, admin: dict = Depends(require_admin)) -> dict:
    require_super(admin)
    username = payload.username.lower().strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    validate_password_strength(payload.password)
    email = str(payload.email).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    existing = await db.admins.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    dupe_email = await db.admins.find_one({"email": email})
    if dupe_email:
        raise HTTPException(status_code=400, detail="Another admin already uses that email")
    perms = [p for p in (payload.permissions or []) if p in ALL_PERMS]
    if payload.isSuper:
        perms = ALL_PERMS.copy()
    doc = {
        "_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "passwordHash": hash_password(payload.password),
        "permissions": perms,
        "isSuper": bool(payload.isSuper),
        "twoFactorEnabled": False,
        "createdAt": datetime.utcnow().isoformat(),
    }
    await db.admins.insert_one(doc)
    return doc_to_admin(doc)


@app.put("/api/admin/admins/{admin_id}")
async def update_admin(admin_id: str, payload: AdminUpdate, admin: dict = Depends(require_admin)) -> dict:
    # Super admins can update anyone; other admins can update themselves (password/email only).
    is_self = admin.get("sub") == admin_id
    if not admin.get("isSuper") and not is_self:
        raise HTTPException(status_code=403, detail="Super admin only")
    doc = await db.admins.find_one({"_id": admin_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    update: dict[str, Any] = {}
    if payload.password:
        validate_password_strength(payload.password)
        update["passwordHash"] = hash_password(payload.password)
    if payload.email is not None:
        new_email = str(payload.email).strip().lower()
        if not new_email:
            raise HTTPException(status_code=400, detail="Email is required")
        if new_email != (doc.get("email") or "").lower():
            dupe = await db.admins.find_one({"email": new_email, "_id": {"$ne": admin_id}})
            if dupe:
                raise HTTPException(status_code=400, detail="Another admin already uses that email")
        update["email"] = new_email
    # Only super admins can change permissions / super flag
    if admin.get("isSuper"):
        if payload.permissions is not None:
            update["permissions"] = [p for p in payload.permissions if p in ALL_PERMS]
        if payload.isSuper is not None:
            update["isSuper"] = bool(payload.isSuper)
            if payload.isSuper:
                update["permissions"] = ALL_PERMS.copy()
    if update:
        await db.admins.update_one({"_id": admin_id}, {"$set": update})
    new_doc = await db.admins.find_one({"_id": admin_id})
    return doc_to_admin(new_doc)


@app.delete("/api/admin/admins/{admin_id}")
async def delete_admin(admin_id: str, admin: dict = Depends(require_admin)) -> dict:
    require_super(admin)
    res = await db.admins.delete_one({"_id": admin_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"ok": True}


# ---- site content ---- #


@app.get("/api/site")
async def get_site(response: Response) -> dict:
    # Ensure no CDN/proxy caches the site config so admin edits reflect immediately across devices
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return await get_site_doc()


@app.put("/api/site")
async def update_site(payload: dict, admin: dict = Depends(require_admin)) -> dict:
    allowed_all = set(default_site().keys())
    is_super = bool(admin.get("isSuper"))
    user_perms = set(admin.get("permissions") or [])

    update_doc: dict[str, Any] = {}
    rejected: list[str] = []
    for k, v in payload.items():
        if k not in allowed_all:
            continue
        if is_super or k in user_perms:
            update_doc[k] = v
        else:
            rejected.append(k)
    if not update_doc:
        raise HTTPException(status_code=403, detail=f"No permitted fields to update. Rejected: {rejected}")
    update_doc["updatedAt"] = datetime.utcnow().isoformat()
    await db.site.update_one({"_id": "main"}, {"$set": update_doc}, upsert=True)
    out = await get_site_doc()
    if rejected:
        out["_rejected"] = rejected
    return out


# ---- uploads (persistent object storage) ---- #

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
STORAGE_PREFIX = "essentialgemstones/uploads"
_storage_key: Optional[str] = None

MEDIA_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".avif": "image/avif",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".m4v": "video/x-m4v",
}


def _init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    if not emergent_key:
        raise RuntimeError("EMERGENT_LLM_KEY missing; object storage unavailable")
    resp = _requests.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _storage_put(path: str, data: bytes, content_type: str) -> dict:
    key = _init_storage()
    resp = _requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def _storage_get(path: str) -> tuple[bytes, str]:
    global _storage_key
    key = _init_storage()
    resp = _requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    if resp.status_code == 403:
        _storage_key = None
        key = _init_storage()
        resp = _requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


@app.post("/api/upload")
async def upload_media(
    file: UploadFile = File(...),
    _admin: dict = Depends(require_admin),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = Path(file.filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        kind = "image"
        max_bytes = MAX_IMAGE_BYTES
    elif ext in VIDEO_EXTENSIONS:
        kind = "video"
        max_bytes = MAX_VIDEO_BYTES
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    buf = _io.BytesIO()
    size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds max size of {max_bytes // (1024 * 1024)}MB",
            )
        buf.write(chunk)

    new_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = f"{STORAGE_PREFIX}/{new_name}"
    content_type = MEDIA_MIME.get(ext, file.content_type or "application/octet-stream")
    try:
        result = await asyncio.to_thread(_storage_put, storage_path, buf.getvalue(), content_type)
    except Exception as exc:  # noqa: BLE001
        logger.error("Object storage upload failed: %s", exc)
        raise HTTPException(status_code=502, detail="Upload storage failed. Please try again.")

    await db.media.insert_one({
        "_id": new_name,
        "storagePath": result.get("path", storage_path),
        "originalFilename": file.filename,
        "contentType": content_type,
        "kind": kind,
        "size": size,
        "createdAt": datetime.utcnow().isoformat(),
    })
    return {"url": f"/api/uploads/{new_name}", "kind": kind, "size": size}


@app.get("/api/uploads/{name}")
async def serve_upload(name: str):
    safe_name = Path(name).name
    record = await db.media.find_one({"_id": safe_name})
    if record:
        try:
            content, ctype = await asyncio.to_thread(_storage_get, record["storagePath"])
            return Response(
                content=content,
                media_type=record.get("contentType") or ctype,
                headers={"Cache-Control": "public, max-age=31536000, immutable"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Object storage fetch failed for %s: %s", safe_name, exc)
    # Legacy fallback: files uploaded before object storage was added
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(file_path)


# ---------------- META ---------------- #


@app.get("/api/permissions")
async def list_permissions() -> dict:
    return {
        "sectionPermissions": SECTION_PERMS,
        "metaPermissions": META_PERMS,
        "all": ALL_PERMS,
    }


# ---------------- EMAIL ---------------- #

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM = os.environ.get("RESEND_FROM", "onboarding@resend.dev").strip()
try:
    import resend as _resend
    if RESEND_API_KEY:
        _resend.api_key = RESEND_API_KEY
except Exception:  # noqa: BLE001
    _resend = None


def _send_email_sync(to_email: str, subject: str, html: str, reply_to: Optional[str] = None, text: Optional[str] = None) -> None:
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP credentials not configured")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_USER))
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    if text is not None:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    else:
        msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def _send_email_resend(to_email: str, subject: str, html: str, reply_to: Optional[str] = None, text: Optional[str] = None) -> str:
    """Send via Resend. Returns the message id. Raises on failure."""
    if not RESEND_API_KEY or _resend is None:
        raise RuntimeError("Resend not configured")
    from_addr = RESEND_FROM
    # If the FROM doesn't include a friendly name, add the brand
    if "<" not in from_addr and " " not in from_addr:
        from_addr = f"{SMTP_FROM_NAME} <{RESEND_FROM}>"
    params: dict[str, Any] = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
    }
    if text is not None:
        params["text"] = text
    else:
        params["html"] = html
    if reply_to:
        params["reply_to"] = [reply_to]
    res = _resend.Emails.send(params)
    return (res or {}).get("id", "")


async def send_email(to_email: str, subject: str, html: str, reply_to: Optional[str] = None, text: Optional[str] = None) -> None:
    """Send an email. Prefers Resend when RESEND_API_KEY is set; falls back to Gmail SMTP.
    Raises the last error if BOTH providers fail (or if neither is configured)."""
    errors: list[str] = []
    if RESEND_API_KEY and _resend is not None:
        try:
            await asyncio.to_thread(_send_email_resend, to_email, subject, html, reply_to, text)
            return
        except Exception as exc:  # noqa: BLE001
            errors.append(f"resend: {exc}")
            logging.warning("Resend send failed, falling back to SMTP: %s", exc)
    if SMTP_USER and SMTP_PASS:
        try:
            await asyncio.to_thread(_send_email_sync, to_email, subject, html, reply_to, text)
            return
        except Exception as exc:  # noqa: BLE001
            errors.append(f"smtp: {exc}")
    raise RuntimeError("Failed to send email: " + " | ".join(errors) if errors else "No email provider configured")


def _admin_notify_html(email: str, when: str) -> str:
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#faf6f0;color:#2c2420;border-radius:16px;">
      <h2 style="font-family:Georgia,serif;color:#1a1410;margin:0 0 8px;">New newsletter subscriber</h2>
      <p style="color:#6b4f3a;margin:0 0 24px;">Someone just joined the Essential Gemstones family.</p>
      <div style="background:#fff;border:1px solid #e8dfd1;border-radius:12px;padding:20px;">
        <p style="margin:0 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.15em;color:#8b6b4f;">Email</p>
        <p style="margin:0 0 18px;font-size:18px;font-weight:600;color:#1a1410;">{email}</p>
        <p style="margin:0 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.15em;color:#8b6b4f;">When</p>
        <p style="margin:0;color:#3d3128;">{when}</p>
      </div>
      <p style="margin:24px 0 0;color:#8b6b4f;font-size:13px;">Sent automatically by your Essential Gemstones site.</p>
    </div>
    """


def _welcome_html(brand: str, founder: str) -> str:
    safe_brand = brand or "Essential Gemstones"
    safe_founder = founder or "Luca"
    return f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#faf6f0;color:#2c2420;border-radius:16px;">
      <p style="font-size:12px;text-transform:uppercase;letter-spacing:.3em;color:#8b6b4f;margin:0 0 12px;">Welcome to the family</p>
      <h1 style="font-family:Georgia,serif;font-size:32px;color:#1a1410;margin:0 0 16px;line-height:1.15;">Thank you for joining, friend.</h1>
      <p style="color:#3d3128;line-height:1.7;margin:0 0 16px;">I\u2019m so glad you\u2019re here. You\u2019ve just joined a small, growing community of crystal lovers and nature seekers who care about meaningful, handmade things.</p>
      <p style="color:#3d3128;line-height:1.7;margin:0 0 16px;">As a subscriber, you\u2019ll be the first to know about new collections, restocks, behind-the-scenes stories from the studio, and special offers \u2014 only for our inner circle.</p>
      <p style="color:#3d3128;line-height:1.7;margin:0 0 32px;">Until then, take a deep breath, hold a stone in your hand, and remember: you carry something powerful within you.</p>
      <div style="border-top:1px solid #e8dfd1;padding-top:24px;">
        <p style="font-family:Georgia,serif;font-style:italic;color:#6b4f3a;font-size:18px;margin:0 0 4px;">With gratitude,</p>
        <p style="font-family:Georgia,serif;color:#1a1410;font-size:20px;margin:0;">{safe_founder}</p>
        <p style="font-size:12px;text-transform:uppercase;letter-spacing:.2em;color:#8b6b4f;margin:4px 0 0;">Founder \u2022 {safe_brand}</p>
      </div>
    </div>
    """


# ---------------- SUBSCRIBERS ---------------- #


class SubscribeIn(BaseModel):
    email: EmailStr


@app.post("/api/subscribe")
async def subscribe(payload: SubscribeIn) -> dict:
    email = str(payload.email).strip().lower()
    site = await get_site_doc()
    footer = site.get("footer") or {}
    admin_email = (footer.get("email") or SMTP_USER or "").strip()
    brand = footer.get("brand") or "Essential Gemstones"
    founder = (site.get("founder") or {}).get("title", "Luca")
    founder_name = founder.replace("Hi, I\u2019m ", "").replace("Hi, I'm ", "").strip() or "Luca"

    now_iso = datetime.utcnow().isoformat()
    existing = await db.subscribers.find_one({"email": email})
    already = existing is not None
    if not already:
        await db.subscribers.insert_one({
            "_id": str(uuid.uuid4()),
            "email": email,
            "createdAt": now_iso,
        })

    when_display = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
    notify_sent = False
    welcome_sent = False
    error: Optional[str] = None
    try:
        if admin_email:
            await send_email(
                admin_email,
                f"New subscriber: {email}",
                _admin_notify_html(email, when_display),
                reply_to=email,
            )
            notify_sent = True
        if not already:
            await send_email(
                email,
                f"Welcome to {brand}",
                _welcome_html(brand, founder_name),
            )
            welcome_sent = True
    except Exception as exc:  # noqa: BLE001
        logger_local = logging.getLogger(__name__)
        logger_local.exception("Email send failed: %s", exc)
        error = str(exc)

    return {
        "ok": True,
        "alreadySubscribed": already,
        "notifySent": notify_sent,
        "welcomeSent": welcome_sent,
        "error": error,
    }


@app.get("/api/admin/subscribers")
async def list_subscribers(admin: dict = Depends(require_admin)) -> list[dict]:
    if not (admin.get("isSuper") or "manage_subscribers" in (admin.get("permissions") or [])):
        raise HTTPException(status_code=403, detail="Forbidden")
    out: list[dict] = []
    cursor = db.subscribers.find().sort("createdAt", -1)
    async for doc in cursor:
        out.append({"id": doc["_id"], "email": doc["email"], "createdAt": doc.get("createdAt")})
    return out


@app.delete("/api/admin/subscribers/{sub_id}")
async def delete_subscriber(sub_id: str, admin: dict = Depends(require_admin)) -> dict:
    if not (admin.get("isSuper") or "manage_subscribers" in (admin.get("permissions") or [])):
        raise HTTPException(status_code=403, detail="Forbidden")
    res = await db.subscribers.delete_one({"_id": sub_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"ok": True}


@app.post("/api/admin/test-email")
async def test_email(payload: dict, admin: dict = Depends(require_admin)) -> dict:
    """Send a quick test email to verify SMTP credentials work."""
    if not admin.get("isSuper"):
        raise HTTPException(status_code=403, detail="Super admin only")
    to = str(payload.get("to") or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="Missing 'to'")
    try:
        await send_email(to, "Test email from Essential Gemstones", _welcome_html("Essential Gemstones", "Luca"))
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------- USER ACCOUNTS ---------------- #


class UserRegisterIn(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    subscribeNewsletter: bool = True


class UserLoginIn(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    fullName: Optional[str] = None
    password: Optional[str] = None


class AdminUserUpdate(BaseModel):
    isBanned: Optional[bool] = None
    fullName: Optional[str] = None


def user_to_public(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "fullName": doc.get("fullName", ""),
        "email": doc.get("email", ""),
        "phone": _mask_phone(doc.get("phone") or "") or None,
        "picture": doc.get("picture", ""),
        "authProvider": doc.get("authProvider", "email"),
        "isBanned": bool(doc.get("isBanned")),
        "favorites": doc.get("favorites", []),
        "createdAt": doc.get("createdAt"),
    }


@app.post("/api/auth/register")
async def auth_register(payload: UserRegisterIn) -> dict:
    full_name = (payload.fullName or "").strip()
    email = str(payload.email).strip().lower()
    if len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Please enter your full name")
    validate_password_strength(payload.password)
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="An account with that email already exists")
    doc = {
        "_id": str(uuid.uuid4()),
        "fullName": full_name,
        "email": email,
        "passwordHash": hash_password(payload.password),
        "isBanned": False,
        "favorites": [],
        "createdAt": datetime.utcnow().isoformat(),
    }
    await db.users.insert_one(doc)

    # Optional newsletter subscribe + welcome emails (best effort)
    if payload.subscribeNewsletter:
        already = await db.subscribers.find_one({"email": email}) is not None
        if not already:
            await db.subscribers.insert_one({
                "_id": str(uuid.uuid4()),
                "email": email,
                "createdAt": datetime.utcnow().isoformat(),
            })
        try:
            site = await get_site_doc()
            footer = site.get("footer") or {}
            admin_email = (footer.get("email") or SMTP_USER or "").strip()
            brand = footer.get("brand") or "Essential Gemstones"
            founder = (site.get("founder") or {}).get("title", "Luca")
            founder_name = founder.replace("Hi, I\u2019m ", "").replace("Hi, I'm ", "").strip() or "Luca"
            when_display = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
            if admin_email:
                await send_email(
                    admin_email,
                    f"New account: {full_name} ({email})",
                    _admin_notify_html(f"{full_name} &lt;{email}&gt;", when_display),
                    reply_to=email,
                )
            await send_email(email, f"Welcome to {brand}", _welcome_html(brand, founder_name))
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).exception("Welcome emails failed: %s", exc)

    token = make_user_token(doc["_id"], doc["email"])
    return {"token": token, "user": user_to_public(doc)}


@app.post("/api/auth/login")
async def auth_login(payload: UserLoginIn) -> dict:
    email = str(payload.email).strip().lower()
    attempt_key = await check_password_attempt(db, "user", email)
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(payload.password, doc.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.password_attempts.delete_one({"_id": attempt_key})
    if doc.get("isBanned"):
        raise HTTPException(status_code=403, detail="Your account has been suspended.")
    token = make_user_token(doc["_id"], doc["email"])
    return {"token": token, "user": user_to_public(doc)}


# ---------- Sign in / sign up with phone (Twilio SMS) ---------- #


class PhoneSendIn(BaseModel):
    phone: str


class PhoneVerifyIn(BaseModel):
    phone: str
    code: str
    fullName: Optional[str] = None


@app.post("/api/auth/phone/send", response_model=PhoneCodeResponse)
async def auth_phone_send(payload: PhoneSendIn) -> dict:
    phone = _normalize_phone(payload.phone)
    return await send_sms_code(db, db.phone_otps, phone, phone, "sign-in")


@app.post("/api/auth/phone/verify")
async def auth_phone_verify(payload: PhoneVerifyIn) -> dict:
    phone = _normalize_phone(payload.phone)
    if not await consume_sms_code(db.phone_otps, phone, payload.code, phone):
        raise HTTPException(status_code=401, detail="Invalid or expired code. Request a new one.")
    # Preserve accounts created under the old ten-digit carrier-gateway format.
    aliases = [phone, phone[2:]] if phone.startswith("+1") else [phone]
    doc = await db.users.find_one({"phone": {"$in": aliases}})
    if doc:
        if doc.get("isBanned"):
            raise HTTPException(status_code=403, detail="Your account has been suspended.")
        await db.users.update_one({"_id": doc["_id"]}, {"$set": {"phone": phone}, "$unset": {"phoneCarrier": ""}})
        doc["phone"] = phone
    else:
        name = (payload.fullName or "").strip()
        doc = {
            "_id": str(uuid.uuid4()),
            "fullName": name if len(name) >= 2 else f"Member \u2022{phone[-4:]}",
            "email": "",
            "phone": phone,
            "passwordHash": "",
            "isBanned": False,
            "favorites": [],
            "authProvider": "phone",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(doc)
    token = make_user_token(doc["_id"], doc.get("email") or "")
    return {"token": token, "user": user_to_public(doc)}


# ---------- Sign in with Google (Emergent-managed OAuth) ---------- #
# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH


class GoogleSessionIn(BaseModel):
    session_id: str


@app.post("/api/auth/google/session")
async def auth_google_session(payload: GoogleSessionIn) -> dict:
    """Exchange an Emergent OAuth session_id for our own user JWT.
    The frontend receives session_id in the URL fragment after the Google flow;
    it posts the id here, we verify it with Emergent, upsert the user by email,
    and hand back a normal user JWT so the rest of the app keeps working."""
    sid = (payload.session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="Missing session id")
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": sid},
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Google sign-in service unreachable: {exc}") from exc
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="This Google sign-in link has expired. Please try again.")
    data = r.json() or {}
    email = str(data.get("email") or "").strip().lower()
    name = str(data.get("name") or "").strip()
    picture = str(data.get("picture") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google didn't share an email for this account.")

    doc = await db.users.find_one({"email": email})
    if doc:
        # Existing member — just log them in and freshen their profile picture/name
        updates: dict[str, Any] = {}
        if name and name != (doc.get("fullName") or ""):
            updates["fullName"] = name
        if picture and picture != (doc.get("picture") or ""):
            updates["picture"] = picture
        if not doc.get("authProvider"):
            updates["authProvider"] = "email+google" if doc.get("passwordHash") else "google"
        if updates:
            await db.users.update_one({"_id": doc["_id"]}, {"$set": updates})
            doc.update(updates)
    else:
        doc = {
            "_id": str(uuid.uuid4()),
            "fullName": name or email.split("@")[0],
            "email": email,
            "passwordHash": "",  # Google users have no local password
            "picture": picture,
            "isBanned": False,
            "favorites": [],
            "authProvider": "google",
            "createdAt": datetime.utcnow().isoformat(),
        }
        await db.users.insert_one(doc)

    if doc.get("isBanned"):
        raise HTTPException(status_code=403, detail="Your account has been suspended.")

    token = make_user_token(doc["_id"], doc["email"])
    return {"token": token, "user": user_to_public(doc)}


@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(require_user)) -> dict:
    doc = await db.users.find_one({"_id": user["sub"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return {"user": user_to_public(doc)}


@app.put("/api/auth/me")
async def auth_update_me(payload: UserProfileUpdate, user: dict = Depends(require_user)) -> dict:
    updates: dict[str, Any] = {}
    if payload.fullName is not None:
        name = payload.fullName.strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Please enter your full name")
        updates["fullName"] = name
    if payload.password is not None:
        if len(payload.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        updates["passwordHash"] = hash_password(payload.password)
    if updates:
        await db.users.update_one({"_id": user["sub"]}, {"$set": updates})
    doc = await db.users.find_one({"_id": user["sub"]})
    return {"user": user_to_public(doc)}


@app.post("/api/auth/favorites/{product_id}")
async def toggle_favorite(product_id: str, user: dict = Depends(require_user)) -> dict:
    if not product_id:
        raise HTTPException(status_code=400, detail="Missing product id")
    doc = await db.users.find_one({"_id": user["sub"]})
    favorites = list(doc.get("favorites", []) if doc else [])
    if product_id in favorites:
        favorites.remove(product_id)
        favorited = False
    else:
        favorites.append(product_id)
        favorited = True
    await db.users.update_one({"_id": user["sub"]}, {"$set": {"favorites": favorites}})
    return {"favorited": favorited, "favorites": favorites}


# ---------------- WAITLIST (notify-me when available) ---------------- #


class WaitlistIn(BaseModel):
    email: Optional[EmailStr] = None


def _product_by_id(site: dict, product_id: str) -> Optional[dict]:
    for it in (site.get("products", {}) or {}).get("items", []) or []:
        if it.get("id") == product_id:
            return it
    return None


@app.post("/api/products/{product_id}/waitlist")
async def join_waitlist(product_id: str, payload: WaitlistIn, request: Request) -> dict:
    """Add a user (logged-in or guest via email) to a product's waitlist."""
    site = await get_site_doc()
    product = _product_by_id(site, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Resolve caller: either a logged-in user via Bearer, or a guest via body.email
    email: Optional[str] = None
    user_id: Optional[str] = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload_jwt = jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALG])
            if payload_jwt.get("role") == "user":
                user_id = payload_jwt.get("sub")
                udoc = await db.users.find_one({"_id": user_id})
                if udoc:
                    email = (udoc.get("email") or "").strip().lower() or None
        except jwt.PyJWTError:
            pass

    if not email:
        email = (str(payload.email).strip().lower() if payload.email else None) or None
    if not email:
        raise HTTPException(status_code=400, detail="Sign in or provide an email to join the waitlist.")

    # Idempotent
    existing = await db.product_waitlist.find_one({"productId": product_id, "email": email})
    if existing:
        return {"ok": True, "already": True, "productId": product_id, "email": _obfuscate_email(email)}

    await db.product_waitlist.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "productId": product_id,
            "productName": product.get("name") or "",
            "email": email,
            "userId": user_id,
            "createdAt": datetime.utcnow().isoformat(),
        }
    )
    return {"ok": True, "already": False, "productId": product_id, "email": _obfuscate_email(email)}


@app.delete("/api/products/{product_id}/waitlist")
async def leave_waitlist(product_id: str, user: dict = Depends(require_user)) -> dict:
    udoc = await db.users.find_one({"_id": user["sub"]})
    email = (udoc.get("email") or "").strip().lower() if udoc else None
    query: dict[str, Any] = {"productId": product_id, "$or": [{"userId": user["sub"]}]}
    if email:
        query["$or"].append({"email": email})
    res = await db.product_waitlist.delete_many(query)
    return {"ok": True, "removed": res.deleted_count}


@app.get("/api/me/waitlist")
async def my_waitlist(user: dict = Depends(require_user)) -> list[dict]:
    udoc = await db.users.find_one({"_id": user["sub"]})
    email = (udoc.get("email") or "").strip().lower() if udoc else None
    q: dict[str, Any] = {"$or": [{"userId": user["sub"]}]}
    if email:
        q["$or"].append({"email": email})
    out: list[dict] = []
    async for r in db.product_waitlist.find(q):
        out.append({"productId": r.get("productId"), "productName": r.get("productName"), "createdAt": r.get("createdAt")})
    return out


@app.get("/api/admin/waitlist")
async def admin_list_waitlist(admin: dict = Depends(require_admin)) -> list[dict]:
    """Admin view of everyone waiting for products."""
    out: list[dict] = []
    async for r in db.product_waitlist.find().sort("createdAt", -1):
        out.append(
            {
                "id": r.get("_id"),
                "productId": r.get("productId"),
                "productName": r.get("productName"),
                "email": r.get("email"),
                "userId": r.get("userId"),
                "createdAt": r.get("createdAt"),
            }
        )
    return out


# ---------------- ADMIN: USER MANAGEMENT ---------------- #


@app.get("/api/admin/users")
async def list_users(admin: dict = Depends(require_admin)) -> list[dict]:
    if not (admin.get("isSuper") or "manage_users" in (admin.get("permissions") or [])):
        raise HTTPException(status_code=403, detail="Forbidden")
    out: list[dict] = []
    cursor = db.users.find().sort("createdAt", -1)
    async for doc in cursor:
        out.append(user_to_public(doc))
    return out


@app.put("/api/admin/users/{user_id}")
async def admin_update_user(user_id: str, payload: AdminUserUpdate, admin: dict = Depends(require_admin)) -> dict:
    if not (admin.get("isSuper") or "manage_users" in (admin.get("permissions") or [])):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db.users.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    update: dict[str, Any] = {}
    if payload.isBanned is not None:
        update["isBanned"] = bool(payload.isBanned)
    if payload.fullName is not None:
        update["fullName"] = payload.fullName.strip()
    if update:
        await db.users.update_one({"_id": user_id}, {"$set": update})
    new_doc = await db.users.find_one({"_id": user_id})
    return user_to_public(new_doc)


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)) -> dict:
    if not (admin.get("isSuper") or "manage_users" in (admin.get("permissions") or [])):
        raise HTTPException(status_code=403, detail="Forbidden")
    res = await db.users.delete_one({"_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


# ---------------- MIDDLEWARE ---------------- #

cors_origins = [origin.strip().rstrip("/") for origin in os.environ["CORS_ORIGINS"].split(",") if origin.strip()]
if not cors_origins or "*" in cors_origins:
    raise RuntimeError("CORS_ORIGINS must explicitly list trusted website origins")
# The trusted preview proxy may forward its configured internal app origin.
if os.environ.get("APP_URL"):
    cors_origins.append(os.environ["APP_URL"].rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def _startup_seed_admin() -> None:
    """One-time migration + self-heal for the built-in super admin.

    - If no admin with username 'master' exists, create one (password from ADMIN_PASSWORD env).
    - If it exists but its stored hash no longer verifies against ADMIN_PASSWORD, re-seed the hash
      (prevents lock-outs after env changes / test drift). Logs a warning when it self-heals.
    - 2FA is NEVER re-enabled or wiped by this hook — that's a manual admin action.
    """
    for collection in (db.phone_otps, db.admin_sms_otps, db.admin_phone_verify, db.sms_send_limits, db.password_attempts):
        await collection.create_index("expires_at", expireAfterSeconds=0)
    try:
        existing_master = await db.admins.find_one({"username": "master"})
        if not existing_master:
            await db.admins.insert_one({
                "_id": str(uuid.uuid4()),
                "username": "master",
                "email": SMTP_USER or None,
                "passwordHash": hash_password(ADMIN_PASSWORD),
                "permissions": ALL_PERMS.copy(),
                "isSuper": True,
                "twoFactorEnabled": False,
                "mustChangePassword": True,
                "createdAt": datetime.utcnow().isoformat(),
                "note": "Built-in super admin (formerly the master password). Change username/password anytime.",
            })
            logger.info("Seeded built-in 'master' super admin from ADMIN_PASSWORD.")
        else:
            stored = existing_master.get("passwordHash", "")
            if not verify_password(ADMIN_PASSWORD, stored):
                # Only self-heal when the CURRENT env password can't unlock the master account.
                # This avoids overwriting a password the admin has intentionally changed.
                # We ONLY heal when the account is still on defaults (no 2FA, mustChangePassword flag set).
                if not existing_master.get("twoFactorEnabled") and existing_master.get("mustChangePassword"):
                    await db.admins.update_one(
                        {"_id": existing_master["_id"]},
                        {"$set": {"passwordHash": hash_password(ADMIN_PASSWORD)}},
                    )
                    logger.warning(
                        "Self-healed 'master' passwordHash from ADMIN_PASSWORD env "
                        "(stored hash no longer matched). Please sign in and change the password."
                    )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup admin seeding failed: %s", exc)


@app.on_event("startup")
async def _startup_storage() -> None:
    """Init object storage and migrate any legacy local uploads into it."""
    try:
        await asyncio.to_thread(_init_storage)
        logger.info("Object storage initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Object storage init failed: %s", exc)
        return

    async def _migrate() -> None:
        for fp in UPLOAD_DIR.iterdir():
            if not fp.is_file():
                continue
            name = fp.name
            if await db.media.find_one({"_id": name}):
                continue
            ext = fp.suffix.lower()
            if ext not in MEDIA_MIME:
                continue
            try:
                data = fp.read_bytes()
                storage_path = f"{STORAGE_PREFIX}/{name}"
                result = await asyncio.to_thread(_storage_put, storage_path, data, MEDIA_MIME[ext])
                await db.media.insert_one({
                    "_id": name,
                    "storagePath": result.get("path", storage_path),
                    "originalFilename": name,
                    "contentType": MEDIA_MIME[ext],
                    "kind": "video" if ext in VIDEO_EXTENSIONS else "image",
                    "size": len(data),
                    "createdAt": datetime.utcnow().isoformat(),
                })
                logger.info("Migrated legacy upload %s to object storage", name)
            except Exception as exc:  # noqa: BLE001
                if "409" in str(exc):
                    await db.media.insert_one({
                        "_id": name,
                        "storagePath": f"{STORAGE_PREFIX}/{name}",
                        "originalFilename": name,
                        "contentType": MEDIA_MIME[ext],
                        "kind": "video" if ext in VIDEO_EXTENSIONS else "image",
                        "size": fp.stat().st_size,
                        "createdAt": datetime.utcnow().isoformat(),
                    })
                    continue
                logger.warning("Legacy upload migration failed for %s: %s", name, exc)

    asyncio.create_task(_migrate())


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()


# ---------------- GEMINI CHAT ---------------- #

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from fastapi.responses import StreamingResponse
import copy as _copy
import json as _json
import re as _re

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
CHAT_PROVIDER = "anthropic"
CHAT_MODEL = "claude-sonnet-4-5"

CHAT_MODES = {"ask-luca", "stone-guide", "admin-writer"}


class ChatMessageIn(BaseModel):
    mode: str
    sessionId: Optional[str] = None
    message: str


def _principal_key(request: Request) -> str:
    """Return a stable user identifier for chat memory.

    Priority: admin JWT sub > user JWT sub > X-Client-Id header > generated.
    """
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        try:
            claims = jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALG])
            role = claims.get("role")
            sub = claims.get("sub")
            if sub:
                if role == "user":
                    return f"user:{sub}"
                return f"admin:{sub}"
        except jwt.PyJWTError:
            pass
    client_id = (request.headers.get("X-Client-Id") or "").strip()
    if client_id:
        return f"anon:{client_id[:80]}"
    return f"anon:{uuid.uuid4()}"


def _require_member_key(request: Request) -> str:
    """Require a valid user or admin JWT for chat access. Anonymous is rejected."""
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please sign in to use the AI chat.")
    try:
        claims = jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    role = claims.get("role")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Please sign in to use the AI chat.")
    if role == "user":
        return f"user:{sub}"
    return f"admin:{sub}"


def _fallback_title_from(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) > 60:
        t = t[:57] + "\u2026"
    return t or "New chat"


def _sanitize_text(s: Any, limit: int = 800) -> str:
    if not s:
        return ""
    text = str(s).strip()
    if len(text) > limit:
        text = text[:limit] + "\u2026"
    return text


async def _build_context_snippets() -> dict[str, str]:
    site = await get_site_doc()
    products = site.get("products", {}).get("items") or []
    faq = site.get("faq", {}).get("items") or []
    stones = site.get("chakra", {}).get("stones") or []
    lava = site.get("lavaMeaning", {}).get("items") or []
    founder = site.get("founder", {})
    craft = site.get("craft", {}).get("steps") or []
    footer = site.get("footer", {})

    products_txt = "\n".join(
        f"- {p.get('name')} ({p.get('price')}): {_sanitize_text(p.get('description'), 240)}"
        for p in products
    ) or "(no products listed)"

    faq_txt = "\n".join(
        f"Q: {f.get('q')}\nA: {_sanitize_text(f.get('a'), 400)}"
        for f in faq
    ) or ""

    stones_txt = "\n".join(
        f"- {s.get('stone')} \u2014 {s.get('chakra')}: {_sanitize_text(s.get('desc'), 240)}"
        for s in stones
    ) or ""

    lava_txt = "\n".join(
        f"- {m.get('title')}: {_sanitize_text(m.get('desc'), 260)}" for m in lava
    ) or ""

    craft_txt = "\n".join(
        f"- {c.get('title')}: {_sanitize_text(c.get('desc'), 240)}" for c in craft
    ) or ""

    founder_intro = _sanitize_text(founder.get("intro"), 500)
    contact_email = footer.get("contactEmail") or footer.get("email") or ""

    return {
        "products": products_txt,
        "faq": faq_txt,
        "stones": stones_txt,
        "lava": lava_txt,
        "craft": craft_txt,
        "founder_intro": founder_intro,
        "contact_email": contact_email,
    }


async def _system_prompt_for(mode: str) -> str:
    ctx = await _build_context_snippets()
    voice_rules = (
        "IMPORTANT VOICE RULES:\n"
        "- Luca is a boy. When referring to Luca, ALWAYS use he/him/his. NEVER use she/her/they.\n"
        "- Do NOT lead descriptions of Luca with his age. Do NOT say phrases like \"nine-year-old entrepreneur\", \"a young boy\", \"kid founder\", or otherwise repeatedly point out how young he is. Just say \"Luca\", \"our founder\", or \"the founder\" \u2014 no age qualifiers unless a visitor explicitly asks about his age.\n"
        "- Speak on behalf of the brand in first-person plural (\"we\", \"our\"). Never refer to yourself as an AI or model.\n"
        "- Do not invent facts, products, prices, or policies that are not present in the reference below.\n"
    )
    if mode == "ask-luca":
        return f"""You are the warm, sincere assistant on Essential Gemstones, a small handmade lava-stone bracelet brand founded by Luca (he/him).

{voice_rules}

STYLE:
- Keep replies short: 2\u20134 sentences unless the visitor asks for detail.
- Sound earthy, human, and honest \u2014 never salesy, never emoji-heavy, never exclamation-heavy.
- If a visitor asks about something not covered below, gently say we don\u2019t have that info yet and offer to connect them with Luca at {ctx['contact_email'] or 'our contact email'}.

REFERENCE (only source of truth):

Products:
{ctx['products']}

FAQ:
{ctx['faq']}

Founder background (for context only \u2014 do NOT quote or paraphrase phrases like "nine-year-old entrepreneur"):
{ctx['founder_intro']}

Craftsmanship:
{ctx['craft']}
"""
    if mode == "stone-guide":
        return f"""You are a gentle, thoughtful chakra & gemstone guide for Essential Gemstones. Help the visitor find the right stone or intention.

{voice_rules}

STYLE:
- Ask 1\u20132 short warm questions if you need more info about what they seek (grounding, protection, focus, love, healing, courage, clarity).
- Then recommend one or two of the stones from the reference below \u2014 poetic but plain, never florid.
- If several stones fit, recommend our 7 Chakra Lava Stone Bracelet.
- Never invent a stone that isn\u2019t in the list.
- Keep it short and inviting.

Available stones on our chakra bracelet:
{ctx['stones']}

What lava stone means to us:
{ctx['lava']}
"""
    if mode == "admin-writer":
        return (
            "You are a creative writing assistant helping the Essential Gemstones team (founder Luca, he/him) write website copy.\n\n"
            + voice_rules
            + "\nSTYLE:\n"
            "- Voice: warm, earthy, sincere, poetic-but-plain. Short sentences. Avoid corporate speak, hype, and exclamation-heavy phrasing. No emojis.\n"
            "- When the user gives you a brief, respond with ONLY the requested copy \u2014 no prefaces, no explanations \u2014 unless they explicitly ask for options or reasoning.\n"
        )
    return "You are a helpful assistant."


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatMessageIn, request: Request) -> StreamingResponse:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="Chat is not configured")
    mode = (payload.mode or "").strip()
    if mode not in CHAT_MODES:
        raise HTTPException(status_code=400, detail="Unknown chat mode")

    # admin-writer requires an admin token
    user_id: Optional[str] = None
    if mode == "admin-writer":
        auth = request.headers.get("Authorization") or ""
        if not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Admin auth required")
        try:
            token = auth.split(" ", 1)[1]
            claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        if claims.get("role") == "user":
            raise HTTPException(status_code=403, detail="Admins only")
        user_id = f"admin:{claims.get('sub')}"
    else:
        # Public chat modes now require member (or admin) auth
        member_key = _require_member_key(request)
        user_id = member_key

    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Message too long")

    session_id = payload.sessionId or str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    user_key = _principal_key(request)

    # Load or create session doc
    session_doc = await db.chat_sessions.find_one({"_id": session_id})
    if session_doc is None:
        session_doc = {
            "_id": session_id,
            "mode": mode,
            "userId": user_id,
            "userKey": user_key,
            "title": _fallback_title_from(text),
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "messages": [],
            "meta": {},
        }
        await db.chat_sessions.insert_one(session_doc)
    else:
        # Enforce ownership: only the same principal (or unowned legacy) may continue a session
        owner = session_doc.get("userKey")
        if owner and owner != user_key:
            raise HTTPException(status_code=403, detail="This chat belongs to another account")
        if session_doc.get("mode") != mode:
            raise HTTPException(status_code=400, detail="Session mode mismatch")
        # Backfill title / userKey for legacy sessions
        if not session_doc.get("title"):
            await db.chat_sessions.update_one({"_id": session_id}, {"$set": {"title": _fallback_title_from(text), "userKey": user_key}})

    # Reconstruct chat with prior history
    system_prompt = await _system_prompt_for(mode)
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(CHAT_PROVIDER, CHAT_MODEL)

    # Replay prior turns so Gemini has full context (llm history is per-instance)
    prior = session_doc.get("messages") or []

    async def event_generator():
        # Warm up prior history via non-streaming send (we won't yield these)
        try:
            for m in prior:
                if m.get("role") == "user":
                    async for _ev in chat.stream_message(UserMessage(text=m.get("content", ""))):
                        if isinstance(_ev, StreamDone):
                            break
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat history replay failed: %s", exc)

        # Yield session id first
        yield f"event: session\ndata: {session_id}\n\n"

        full_reply = ""
        try:
            async for ev in chat.stream_message(UserMessage(text=text)):
                if isinstance(ev, TextDelta):
                    chunk = ev.content or ""
                    full_reply += chunk
                    # SSE data lines cannot contain literal newlines; escape them
                    escaped = chunk.replace("\r", "").replace("\n", "\\n")
                    yield f"data: {escaped}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat stream failed: %s", exc)
            yield f"event: error\ndata: {str(exc)[:200]}\n\n"

        # Persist to db (best effort)
        try:
            new_messages = prior + [
                {"role": "user", "content": text, "at": now_iso},
                {"role": "assistant", "content": full_reply, "at": datetime.utcnow().isoformat()},
            ]
            await db.chat_sessions.update_one(
                {"_id": session_id},
                {"$set": {"messages": new_messages, "updatedAt": datetime.utcnow().isoformat()}},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat persist failed: %s", exc)

        yield "event: done\ndata: end\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/chat/session/{session_id}")
async def get_chat_session(session_id: str, request: Request) -> dict:
    user_key = _require_member_key(request)
    doc = await db.chat_sessions.find_one({"_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    owner = doc.get("userKey")
    if owner and owner != user_key:
        raise HTTPException(status_code=403, detail="Not your chat")
    return {
        "id": doc["_id"],
        "mode": doc.get("mode"),
        "title": doc.get("title") or "",
        "messages": doc.get("messages") or [],
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),
    }


@app.get("/api/chat/sessions")
async def list_my_chat_sessions(request: Request, mode: Optional[str] = None, limit: int = 100) -> list[dict]:
    user_key = _require_member_key(request)
    query: dict[str, Any] = {"userKey": user_key}
    if mode:
        query["mode"] = mode
    cursor = db.chat_sessions.find(query).sort("updatedAt", -1).limit(max(1, min(limit, 500)))
    out: list[dict] = []
    async for doc in cursor:
        msgs = doc.get("messages") or []
        last = msgs[-1] if msgs else None
        out.append({
            "id": doc["_id"],
            "mode": doc.get("mode"),
            "title": doc.get("title") or (msgs[0].get("content", "New chat")[:60] if msgs else "New chat"),
            "createdAt": doc.get("createdAt"),
            "updatedAt": doc.get("updatedAt"),
            "messageCount": len(msgs),
            "lastMessagePreview": ((last.get("content") or "")[:140] if last else ""),
        })
    return out


class SessionRenameIn(BaseModel):
    title: str


@app.put("/api/chat/session/{session_id}")
async def rename_chat_session(session_id: str, payload: SessionRenameIn, request: Request) -> dict:
    user_key = _require_member_key(request)
    doc = await db.chat_sessions.find_one({"_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    owner = doc.get("userKey")
    if owner and owner != user_key:
        raise HTTPException(status_code=403, detail="Not your chat")
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if len(title) > 200:
        title = title[:200]
    await db.chat_sessions.update_one({"_id": session_id}, {"$set": {"title": title}})
    return {"ok": True, "title": title}


@app.delete("/api/chat/session/{session_id}")
async def delete_my_chat_session(session_id: str, request: Request) -> dict:
    user_key = _require_member_key(request)
    doc = await db.chat_sessions.find_one({"_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    owner = doc.get("userKey")
    if owner and owner != user_key:
        raise HTTPException(status_code=403, detail="Not your chat")
    await db.chat_sessions.delete_one({"_id": session_id})
    return {"ok": True}


@app.get("/api/admin/chat-sessions")
async def admin_list_chat_sessions(admin: dict = Depends(require_admin), limit: int = 100) -> list[dict]:
    cursor = db.chat_sessions.find().sort("updatedAt", -1).limit(max(1, min(limit, 500)))
    out: list[dict] = []
    async for doc in cursor:
        msgs = doc.get("messages") or []
        out.append({
            "id": doc["_id"],
            "mode": doc.get("mode"),
            "createdAt": doc.get("createdAt"),
            "updatedAt": doc.get("updatedAt"),
            "userId": doc.get("userId"),
            "messageCount": len(msgs),
            "lastMessage": (msgs[-1].get("content")[:180] if msgs else ""),
        })
    return out


@app.delete("/api/admin/chat-sessions/{session_id}")
async def admin_delete_chat_session(session_id: str, admin: dict = Depends(require_admin)) -> dict:
    res = await db.chat_sessions.delete_one({"_id": session_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ---------------- AI SITE EDITOR (auto-apply with undo) ---------------- #


class AIEditIn(BaseModel):
    message: str


class AIUndoIn(BaseModel):
    snapshot: dict


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort JSON extraction from an LLM reply."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown code fences ```json ... ``` or ``` ... ```
    fence = _re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```\s*$", text)
    if fence:
        text = fence.group(1).strip()
    # Try raw
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass
    # Fallback: greediest first-{ last-}
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return _json.loads(text[start : end + 1])
        except _json.JSONDecodeError:
            return None
    return None


def _set_at_path(root: dict, path: str, value: Any) -> None:
    """Set value at dotted path with optional [n] array indices.

    Examples:
      hero.subtitle
      products.items[0].description
      sectionVisibility.faq
    """
    segments = path.split(".")
    cur: Any = root
    for i, seg in enumerate(segments):
        is_last = i == len(segments) - 1
        m = _re.match(r"^([^\[\]]+)(?:\[(\d+)\])?$", seg)
        if not m:
            raise ValueError(f"Bad path segment: {seg}")
        key = m.group(1)
        idx = m.group(2)
        if idx is None:
            if is_last:
                cur[key] = value
                return
            nxt = cur.get(key)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[key] = nxt
            cur = nxt
        else:
            n = int(idx)
            arr = cur.get(key)
            if not isinstance(arr, list):
                arr = []
                cur[key] = arr
            while len(arr) <= n:
                arr.append({})
            if is_last:
                arr[n] = value
                return
            if not isinstance(arr[n], (dict, list)):
                arr[n] = {}
            cur = arr[n]


@app.post("/api/admin/ai-edit")
async def ai_edit_site(payload: AIEditIn, admin: dict = Depends(require_admin)) -> dict:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI is not configured")
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Message too long")

    site = await get_site_doc()
    snapshot = _copy.deepcopy(site)

    schema_keys = list(default_site().keys())
    system_prompt = (
        "You are the site editor for Essential Gemstones, a handmade lava-stone bracelet brand founded by Luca (he/him). "
        "You EDIT the site content in response to instructions from the admin.\n\n"
        "VOICE: warm, earthy, sincere, short sentences. No exclamation-heavy hype. No emojis. Never refer to Luca as she/her/they. Never lead descriptions of Luca with his age (no \"nine-year-old\", \"young founder\").\n\n"
        "OUTPUT FORMAT: Respond with ONLY a single JSON object (no prose, no code fences) in this exact shape:\n"
        "{\n  \"summary\": \"<one-sentence description of what you changed>\",\n"
        "  \"edits\": [\n    {\"path\": \"<dotted path>\", \"value\": <new value: string | number | boolean | array | object>}\n  ]\n}\n\n"
        "PATH SYNTAX:\n"
        "- Dot notation to descend into objects. Bracket [n] to select an array index. Example: products.items[0].description, sectionVisibility.faq, sectionOrder.\n"
        "- To replace an entire array, set path to the array key and value to the new array.\n"
        f"- Top-level keys you may edit: {schema_keys}.\n\n"
        "RULES:\n"
        "- Make MINIMAL, TARGETED edits. Only change what the admin asked for. Do not rewrite unrelated fields.\n"
        "- Preserve existing structure. Do not remove keys the site uses. Never invent fields the schema doesn't have.\n"
        "- If the admin asks for something impossible or unsafe, return {\"summary\": \"<explain>\", \"edits\": []} and no edits.\n"
        "- If the admin asks you to remove something, either set the string to \"\" or omit the item from the array by outputting the new array.\n\n"
        "CURRENT SITE CONTENT (JSON):\n"
        + _json.dumps(site, ensure_ascii=False)
    )

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"ai-edit-{uuid.uuid4()}",
        system_message=system_prompt,
    ).with_model(CHAT_PROVIDER, CHAT_MODEL)

    try:
        reply = await chat.send_message(UserMessage(text=text))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")

    parsed = _extract_json(reply)
    if not parsed or not isinstance(parsed, dict):
        return {"summary": "The assistant did not return a valid edit plan.", "applied": [], "failed": [], "snapshot": snapshot, "raw": reply[:800]}

    summary = str(parsed.get("summary") or "").strip()
    edits = parsed.get("edits") or []
    if not isinstance(edits, list):
        edits = []

    applied: list[dict] = []
    failed: list[dict] = []
    updated = _copy.deepcopy(site)
    allowed = set(default_site().keys())
    for e in edits:
        if not isinstance(e, dict):
            failed.append({"edit": e, "reason": "not an object"})
            continue
        path = str(e.get("path") or "").strip()
        if not path:
            failed.append({"edit": e, "reason": "missing path"})
            continue
        top = path.split(".")[0].split("[")[0]
        if top not in allowed:
            failed.append({"edit": e, "reason": f"top-level key '{top}' not editable"})
            continue
        try:
            _set_at_path(updated, path, e.get("value"))
            applied.append({"path": path, "value": e.get("value")})
        except Exception as exc:  # noqa: BLE001
            failed.append({"edit": e, "reason": str(exc)})

    if applied:
        # Persist
        update_doc = {k: v for k, v in updated.items() if k in allowed}
        update_doc["updatedAt"] = datetime.utcnow().isoformat()
        await db.site.update_one({"_id": "main"}, {"$set": update_doc}, upsert=True)

    return {
        "summary": summary or (f"Applied {len(applied)} edit(s)." if applied else "No changes applied."),
        "applied": applied,
        "failed": failed,
        "snapshot": snapshot,
    }


@app.post("/api/admin/ai-edit/undo")
async def ai_edit_undo(payload: AIUndoIn, admin: dict = Depends(require_admin)) -> dict:
    snap = payload.snapshot or {}
    if not isinstance(snap, dict) or not snap:
        raise HTTPException(status_code=400, detail="Missing snapshot")
    allowed = set(default_site().keys())
    update_doc = {k: v for k, v in snap.items() if k in allowed}
    if not update_doc:
        raise HTTPException(status_code=400, detail="Empty snapshot")
    update_doc["updatedAt"] = datetime.utcnow().isoformat()
    await db.site.update_one({"_id": "main"}, {"$set": update_doc}, upsert=True)
    return {"ok": True}


# ---------------- UNIFIED ADMIN AI (chat + edit + email broadcast) ---------------- #


class AdminAIIn(BaseModel):
    message: str
    sessionId: Optional[str] = None


def _generate_strong_password(length: int = 14) -> str:
    """Return a password that is GUARANTEED to satisfy validate_password_strength."""
    upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I, O
    lower = "abcdefghijkmnpqrstuvwxyz"  # no l, o
    digits = "23456789"                  # no 0, 1
    symbols = "!@#$%^&*"
    all_chars = upper + lower + digits + symbols
    rng = _secrets.SystemRandom()
    chars = [
        rng.choice(upper),
        rng.choice(lower),
        rng.choice(digits),
        rng.choice(symbols),
    ]
    chars += [rng.choice(all_chars) for _ in range(max(0, length - 4))]
    rng.shuffle(chars)
    return "".join(chars)


async def _apply_admin_action(action_obj: dict, caller: dict) -> dict:
    """Execute an admin-management action requested by the Admin AI.
    Only reachable when the caller is a super admin (checked in the endpoint).
    Returns a shape suitable for the frontend: {ok, summary?, error?, target?, generatedPassword?}.
    """
    if not isinstance(action_obj, dict):
        return {"ok": False, "error": "no action provided"}
    action = str(action_obj.get("action") or "").strip().lower()
    if action not in {"create", "update", "delete", "resetpassword", "reset2fa"}:
        return {"ok": False, "error": f"unknown action '{action}'"}

    async def _find_target() -> Optional[dict]:
        target_id = str(action_obj.get("id") or "").strip()
        if target_id:
            return await db.admins.find_one({"_id": target_id})
        target_username = str(action_obj.get("username") or "").strip().lower()
        if target_username:
            return await db.admins.find_one({"username": target_username})
        return None

    if action == "create":
        username = str(action_obj.get("username") or "").strip().lower()
        email = str(action_obj.get("email") or "").strip().lower()
        password = str(action_obj.get("password") or "").strip()
        generated = False
        if not username:
            return {"ok": False, "error": "username is required to create an admin"}
        if not email or "@" not in email:
            return {"ok": False, "error": "a valid email is required to create an admin"}
        if not password:
            password = _generate_strong_password()
            generated = True
        try:
            validate_password_strength(password)
        except HTTPException as exc:
            return {"ok": False, "error": exc.detail}
        if await db.admins.find_one({"username": username}):
            return {"ok": False, "error": f"an admin named '{username}' already exists"}
        if await db.admins.find_one({"email": email}):
            return {"ok": False, "error": f"another admin already uses {email}"}
        is_super_new = bool(action_obj.get("isSuper"))
        perms = [p for p in (action_obj.get("permissions") or []) if p in ALL_PERMS]
        if is_super_new:
            perms = ALL_PERMS.copy()
        new_doc = {
            "_id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "passwordHash": hash_password(password),
            "permissions": perms,
            "isSuper": is_super_new,
            "twoFactorEnabled": False,
            "createdAt": datetime.utcnow().isoformat(),
        }
        await db.admins.insert_one(new_doc)
        summary = f"Created admin '{username}' ({email})."
        if generated:
            summary += f" Temporary password: {password} (share this once; they should change it after signing in)."
        return {
            "ok": True,
            "action": "create",
            "target": doc_to_admin(new_doc),
            "summary": summary,
            "generatedPassword": password if generated else None,
        }

    target = await _find_target()
    if not target:
        return {"ok": False, "error": "target admin not found"}
    # Self-preservation: refuse to delete or demote the caller from a super-only account
    is_self = target["_id"] == caller.get("sub")

    if action == "update":
        update: dict[str, Any] = {}
        if action_obj.get("email") is not None:
            new_email = str(action_obj.get("email") or "").strip().lower()
            if not new_email or "@" not in new_email:
                return {"ok": False, "error": "email must be a valid address"}
            if new_email != (target.get("email") or "").lower():
                dupe = await db.admins.find_one({"email": new_email, "_id": {"$ne": target["_id"]}})
                if dupe:
                    return {"ok": False, "error": f"another admin already uses {new_email}"}
            update["email"] = new_email
        if action_obj.get("permissions") is not None:
            update["permissions"] = [p for p in action_obj["permissions"] if p in ALL_PERMS]
        if action_obj.get("isSuper") is not None:
            new_super = bool(action_obj.get("isSuper"))
            if is_self and not new_super and target.get("isSuper"):
                return {"ok": False, "error": "you can\u2019t remove your own super-admin flag"}
            update["isSuper"] = new_super
            if new_super:
                update["permissions"] = ALL_PERMS.copy()
        if action_obj.get("username") is not None and str(action_obj.get("username")).strip().lower() != target.get("username"):
            # Explicit rename is allowed
            new_username = str(action_obj["username"]).strip().lower()
            if not new_username:
                return {"ok": False, "error": "username can\u2019t be blank"}
            if await db.admins.find_one({"username": new_username, "_id": {"$ne": target["_id"]}}):
                return {"ok": False, "error": f"another admin is already named '{new_username}'"}
            update["username"] = new_username
        if not update:
            return {"ok": False, "error": "nothing to update"}
        await db.admins.update_one({"_id": target["_id"]}, {"$set": update})
        fresh = await db.admins.find_one({"_id": target["_id"]})
        return {"ok": True, "action": "update", "target": doc_to_admin(fresh), "summary": f"Updated '{fresh['username']}': {', '.join(update.keys())}."}

    if action == "delete":
        if is_self:
            return {"ok": False, "error": "you can\u2019t delete your own account"}
        await db.admins.delete_one({"_id": target["_id"]})
        await db.admin_trusted_devices.delete_many({"adminId": target["_id"]})
        await db.admin_email_otps.delete_one({"_id": target["_id"]})
        await revoke_admin_codes(db, target["_id"])
        return {"ok": True, "action": "delete", "summary": f"Deleted admin '{target.get('username')}'."}

    if action == "resetpassword":
        password = str(action_obj.get("password") or "").strip()
        generated = False
        if not password:
            password = _generate_strong_password()
            generated = True
        try:
            validate_password_strength(password)
        except HTTPException as exc:
            return {"ok": False, "error": exc.detail}
        await db.admins.update_one({"_id": target["_id"]}, {"$set": {"passwordHash": hash_password(password)}})
        summary = f"Reset password for '{target.get('username')}'."
        if generated:
            summary += f" Temporary password: {password}"
        return {"ok": True, "action": "resetPassword", "summary": summary, "generatedPassword": password if generated else None}

    if action == "reset2fa":
        await db.admins.update_one(
            {"_id": target["_id"]},
            {"$unset": {"twoFactorSecret": "", "twoFactorEnabled": "", "twoFactorBackupCodes": "", "twoFactorPendingSecret": "", "twoFactorEnabledAt": ""}},
        )
        await db.admin_trusted_devices.delete_many({"adminId": target["_id"]})
        await db.admin_email_otps.delete_one({"_id": target["_id"]})
        await revoke_admin_codes(db, target["_id"])
        return {"ok": True, "action": "reset2fa", "summary": f"Reset 2FA for '{target.get('username')}'. They\u2019ll enroll again on their next login."}

    return {"ok": False, "error": f"unhandled action '{action}'"}


def _unified_admin_prompt(site_json: str, subscriber_count: int, admins_json: str, is_super: bool) -> str:
    schema_keys = list(default_site().keys())
    admins_block = (
        "\n\nCURRENT ADMINS (JSON list, passwordHash excluded):\n" + admins_json
        if is_super
        else ""
    )
    admins_action_doc = (
        "- 'admins' \u2192 the admin wants to create, edit, delete, reset the password, or reset 2FA of another admin account. "
        "ONLY available to super admins. Fill 'admins' with a single action object. Confirm the change in 'reply'.\n"
        "  Shape:\n"
        "  { \"action\": \"create\" | \"update\" | \"delete\" | \"resetPassword\" | \"reset2fa\",\n"
        "    \"id\": \"<admin_id>\",            // required for update/delete/resetPassword/reset2fa\n"
        "    \"username\": \"<new-or-existing username>\",  // required for create; optional lookup for update if id unknown\n"
        "    \"email\": \"<email@example.com>\", // required for create, optional for update\n"
        "    \"password\": \"<strong password>\", // required for create and resetPassword; must meet policy\n"
        "    \"permissions\": [\"hero\", \"products\", ...],  // optional, ignored when isSuper=true\n"
        "    \"isSuper\": true|false            // optional\n"
        "  }\n"
        "  Password policy: min 8 chars, one uppercase, one lowercase, one digit, one symbol. If the admin asks you "
        "to create an admin without giving a password, generate a strong random one and INCLUDE it in 'reply' so they can share it.\n"
        "  Email is REQUIRED when creating an admin. Never make one up \u2014 ask the admin for it if they didn't provide one (kind='chat').\n"
        if is_super
        else "- 'admins' \u2192 NOT available. You are not a super admin. Reply as 'chat' and explain the caller needs super-admin rights.\n"
    )
    return (
        "You are the SITE OWNER'S personal AI for Essential Gemstones, a handmade lava-stone bracelet brand "
        "founded by Luca (he/him, nine years old). You act on behalf of the admin. You can hold a normal "
        "conversation, draft copy, EDIT the live site, PREVIEW a section of the live site inside the chat, "
        "SEND emails to any recipients, or (super admins only) MANAGE OTHER ADMIN ACCOUNTS. Choose the ONE "
        "action that best fits the admin's request.\n\n"
        "VOICE: warm, earthy, sincere, plain and grounded. Short sentences. No exclamation-heavy hype, no emojis. "
        "Never refer to Luca as she/her/they. Never lead descriptions of Luca with his age.\n\n"
        "OUTPUT FORMAT: Reply with ONLY a single JSON object (no prose outside JSON, no code fences). Exact shape:\n"
        "{\n"
        '  "kind": "chat" | "edit" | "preview" | "email" | "admins",\n'
        '  "reply": "<what to show the admin>",\n'
        '  "edits": [ {"path": "<dotted path>", "value": <new value>} ],\n'
        '  "preview": { "section": "hero"|"products"|"faq"|"about"|"story"|"founder"|"members"|"chakra"|"full", "note": "<what to look at>" },\n'
        '  "email": { "subject": "<subject line>", "html": "<well-formatted HTML body>", "to": <recipients> },\n'
        '  "admins": { "action": "...", ... }\n'
        "}\n"
        "Only include 'edits' when kind='edit'. Only include 'preview' when kind='preview'. Only include 'email' "
        "when kind='email'. Only include 'admins' when kind='admins'. 'reply' is ALWAYS required.\n\n"
        "WHEN TO PICK EACH kind:\n"
        "- 'chat'  \u2192 the admin is asking a question, brainstorming, or wants you to draft copy without applying it. "
        "Put the draft or answer in 'reply'.\n"
        "- 'edit'  \u2192 the admin wants a live change to the website (hero, products, FAQ, colors of copy, section order, "
        "visibility, footer, etc.). Fill 'edits' with MINIMAL, TARGETED paths and put a one-sentence summary in 'reply'.\n"
        "- 'preview' \u2192 the admin wants to SEE something on the site (e.g. 'show me the hero', 'what does the products "
        "section look like right now?', 'let me see the FAQ', 'preview the footer'). Set preview.section to one of "
        "'hero','products','faq','about','story','founder','members','chakra', or 'full' for the whole page. "
        "Use preview.note to point out what they should notice. Also pick 'preview' when the admin asks you to preview "
        "a change you just made or want to make.\n"
        "- 'email' \u2192 the admin wants an email drafted and (after they confirm) sent. Write a real, warm HTML email "
        "in 'email.html' using inline styles suitable for email clients. Choose 'email.to' based on the audience the "
        "admin describes:\n"
        f"    * \"subscribers\" (default) \u2013 every newsletter subscriber (current count: {subscriber_count}).\n"
        "    * \"members\" \u2013 every signed-up member/user account.\n"
        "    * \"admins\" \u2013 every admin account with an email on file.\n"
        "    * \"all\" \u2013 union of subscribers + members + admins.\n"
        "    * A JSON list of specific email addresses \u2013 for one-off messages, e.g. [\"friend@example.com\"].\n"
        "    * A single email address string \u2013 for messaging one specific person.\n"
        "  Put a short confirmation in 'reply' like 'Draft ready. Say send it to email <audience>.' The admin will "
        "review the recipients + copy before it actually goes out. If the admin says 'send an email to <name>' but "
        "hasn\u2019t given an address, ASK for the address in 'reply' with kind='chat'.\n"
        + admins_action_doc +
        "\nEDIT PATH SYNTAX:\n"
        "- Dot notation to descend into objects. Bracket [n] to select an array index. "
        "Example: products.items[0].description, sectionVisibility.faq, sectionOrder.\n"
        "- To replace an entire array, set path to the array key and value to the new array.\n"
        f"- Top-level keys you may edit: {schema_keys}.\n\n"
        "RULES:\n"
        "- Do EXACTLY what the admin asked \u2014 no more, no less. Do not rewrite unrelated fields.\n"
        "- Preserve existing structure. Do not remove keys the site uses. Never invent fields the schema doesn't have.\n"
        "- If the request is unsafe/impossible, set kind='chat' and explain in 'reply'.\n"
        "- Never expose passwordHash, twoFactorSecret, or backup codes verbatim.\n\n"
        "CURRENT SITE CONTENT (JSON):\n" + site_json
        + admins_block
    )


@app.post("/api/admin/ai")
async def admin_ai_unified(payload: AdminAIIn, request: Request, admin: dict = Depends(require_admin)) -> dict:
    """Single all-powerful admin AI. Auto-decides chat vs edit vs email broadcast."""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI is not configured")
    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    if len(text) > 6000:
        raise HTTPException(status_code=400, detail="Message too long")

    site = await get_site_doc()
    subscribers_count = await db.subscribers.count_documents({})
    snapshot = _copy.deepcopy(site)
    site_json = _json.dumps(site, ensure_ascii=False)
    is_super = bool(admin.get("isSuper"))
    admins_json = "[]"
    if is_super:
        cursor = db.admins.find({}, {"passwordHash": 0, "twoFactorSecret": 0, "twoFactorPendingSecret": 0, "twoFactorBackupCodes": 0})
        rows = []
        async for a_doc in cursor:
            rows.append(
                {
                    "id": a_doc.get("_id"),
                    "username": a_doc.get("username"),
                    "email": a_doc.get("email"),
                    "permissions": a_doc.get("permissions", []),
                    "isSuper": bool(a_doc.get("isSuper")),
                    "twoFactorEnabled": bool(a_doc.get("twoFactorEnabled")),
                    "createdAt": a_doc.get("createdAt"),
                }
            )
        admins_json = _json.dumps(rows, ensure_ascii=False)
    system_prompt = _unified_admin_prompt(site_json, subscribers_count, admins_json, is_super)

    # Session memory: reuse chat_sessions collection with mode 'admin-writer'
    now_iso = datetime.utcnow().isoformat()
    user_key = f"admin:{admin.get('sub')}"
    session_id = payload.sessionId or str(uuid.uuid4())
    session_doc = await db.chat_sessions.find_one({"_id": session_id})
    if session_doc is None:
        session_doc = {
            "_id": session_id,
            "mode": "admin-writer",
            "userId": user_key,
            "userKey": user_key,
            "title": _fallback_title_from(text),
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "messages": [],
            "meta": {},
        }
        await db.chat_sessions.insert_one(session_doc)
    else:
        owner = session_doc.get("userKey")
        if owner and owner != user_key:
            raise HTTPException(status_code=403, detail="This chat belongs to another admin.")

    prior = session_doc.get("messages") or []

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(CHAT_PROVIDER, CHAT_MODEL)

    # Warm up prior history in the model (best-effort)
    try:
        for m in prior[-20:]:
            if m.get("role") == "user":
                async for _ev in chat.stream_message(UserMessage(text=m.get("content", ""))):
                    if isinstance(_ev, StreamDone):
                        break
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin-ai history replay failed: %s", exc)

    try:
        reply_raw = await chat.send_message(UserMessage(text=text))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")

    parsed = _extract_json(reply_raw) or {}
    kind = str(parsed.get("kind") or "chat").lower().strip()
    reply_text = str(parsed.get("reply") or "").strip() or (reply_raw[:800] if reply_raw else "")

    result: dict[str, Any] = {
        "sessionId": session_id,
        "kind": kind,
        "reply": reply_text,
        "applied": [],
        "failed": [],
        "snapshot": None,
        "emailSent": False,
        "emailStats": None,
        "adminAction": None,
        "preview": None,
    }

    # --- Handle EDIT ---
    if kind == "edit":
        edits = parsed.get("edits") or []
        if not isinstance(edits, list):
            edits = []
        applied: list[dict] = []
        failed: list[dict] = []
        updated = _copy.deepcopy(site)
        allowed = set(default_site().keys())
        for e in edits:
            if not isinstance(e, dict):
                failed.append({"edit": e, "reason": "not an object"})
                continue
            path = str(e.get("path") or "").strip()
            if not path:
                failed.append({"edit": e, "reason": "missing path"})
                continue
            top = path.split(".")[0].split("[")[0]
            if top not in allowed:
                failed.append({"edit": e, "reason": f"top-level key '{top}' not editable"})
                continue
            try:
                _set_at_path(updated, path, e.get("value"))
                applied.append({"path": path, "value": e.get("value")})
            except Exception as exc:  # noqa: BLE001
                failed.append({"edit": e, "reason": str(exc)})
        if applied:
            update_doc = {k: v for k, v in updated.items() if k in allowed}
            update_doc["updatedAt"] = datetime.utcnow().isoformat()
            await db.site.update_one({"_id": "main"}, {"$set": update_doc}, upsert=True)
        result["applied"] = applied
        result["failed"] = failed
        result["snapshot"] = snapshot
        if not reply_text:
            result["reply"] = f"Applied {len(applied)} change(s)." if applied else "No changes applied."

    # --- Handle EMAIL DRAFT (any recipients) ---
    elif kind == "email":
        email_obj = parsed.get("email") or {}
        subject = str(email_obj.get("subject") or "").strip()
        html = str(email_obj.get("html") or "").strip()
        to_spec = email_obj.get("to")
        if to_spec is None:
            to_spec = "subscribers"
        recipients, audience_label = await _resolve_email_audience(to_spec)
        if not subject or not html:
            result["kind"] = "chat"
            result["reply"] = (reply_text or "") + "\n\n(I didn\u2019t have a subject/body ready \u2014 tell me what to say and I\u2019ll draft it.)"
        else:
            # Draft-only: admin confirms via /api/admin/ai/email/send
            result["emailDraft"] = {
                "subject": subject,
                "html": html,
                "to": recipients,
                "toSpec": to_spec if isinstance(to_spec, (str, list)) else "subscribers",
                "audience": audience_label,
                "recipientCount": len(recipients),
            }
            if not reply_text:
                if recipients:
                    result["reply"] = f"Draft is ready \u2014 preview below. Say \u2018send it\u2019 to email {audience_label} ({len(recipients)} recipient{'s' if len(recipients) != 1 else ''})."
                else:
                    result["reply"] = f"Draft is ready \u2014 but I couldn\u2019t find any {audience_label} to send to. Tell me who should receive it."

    # --- Handle PREVIEW (show the admin a live section of the site inside chat) ---
    elif kind == "preview":
        preview_obj = parsed.get("preview") or {}
        section = str(preview_obj.get("section") or "full").strip().lower()
        # Map section name -> anchor id used on the public site
        anchor_map = {
            "hero": "top",
            "top": "top",
            "products": "shop",
            "shop": "shop",
            "faq": "faq",
            "about": "story",
            "story": "story",
            "founder": "founder",
            "members": "members",
            "vip": "members",
            "chakra": "chakra",
            "full": "",
            "home": "",
        }
        if section not in anchor_map:
            section = "full"
        anchor = anchor_map[section]
        result["preview"] = {
            "section": section,
            "anchor": anchor,
            "note": str(preview_obj.get("note") or "").strip(),
        }
        if not reply_text:
            result["reply"] = f"Here\u2019s a live look at the {section} section." if section != "full" else "Here\u2019s the whole site as it looks right now."

    # --- Handle ADMIN MANAGEMENT (super admins only) ---
    elif kind == "admins":
        if not is_super:
            result["kind"] = "chat"
            result["reply"] = (reply_text or "") + "\n\n(You need super-admin rights to manage admin accounts. Ask a super admin.)"
        else:
            action_result = await _apply_admin_action(parsed.get("admins") or {}, admin)
            result["adminAction"] = action_result
            if not reply_text:
                if action_result.get("ok"):
                    result["reply"] = action_result.get("summary") or "Done."
                else:
                    result["reply"] = f"Couldn\u2019t do that: {action_result.get('error') or 'unknown error'}."

    # --- Persist chat memory ---
    try:
        new_messages = prior + [
            {"role": "user", "content": text, "at": now_iso},
            {"role": "assistant", "content": reply_text or "(no reply)", "at": datetime.utcnow().isoformat(), "kind": kind},
        ]
        await db.chat_sessions.update_one(
            {"_id": session_id},
            {"$set": {"messages": new_messages, "updatedAt": datetime.utcnow().isoformat()}},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin-ai persist failed: %s", exc)

    return result


class AdminBroadcastIn(BaseModel):
    subject: str
    html: str
    to: Optional[Any] = None  # list of emails, or one of {"subscribers","admins","users","all"}


async def _resolve_email_audience(audience: Any) -> tuple[list[str], str]:
    """Turn an audience spec into a de-duped list of email addresses.
    Accepts: list of emails, a single email string, or the keywords
    'subscribers' (default), 'admins', 'users', 'all'.
    Returns (emails, label)."""
    label = "subscribers"
    emails: list[str] = []
    email_re = _pw_re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    async def _subs() -> list[str]:
        out: list[str] = []
        async for doc in db.subscribers.find():
            e = (doc.get("email") or "").strip().lower()
            if e:
                out.append(e)
        return out

    async def _admins() -> list[str]:
        out: list[str] = []
        async for doc in db.admins.find():
            e = (doc.get("email") or "").strip().lower()
            if e:
                out.append(e)
        return out

    async def _users() -> list[str]:
        out: list[str] = []
        async for doc in db.users.find():
            e = (doc.get("email") or "").strip().lower()
            if e:
                out.append(e)
        return out

    if audience is None or (isinstance(audience, str) and audience.strip().lower() in {"subscribers", "subscriber", "newsletter"}):
        emails = await _subs()
        label = "subscribers"
    elif isinstance(audience, str) and audience.strip().lower() == "admins":
        emails = await _admins()
        label = "admins"
    elif isinstance(audience, str) and audience.strip().lower() in {"users", "members"}:
        emails = await _users()
        label = "members"
    elif isinstance(audience, str) and audience.strip().lower() == "all":
        emails = list({*(await _subs()), *(await _users()), *(await _admins())})
        label = "everyone (subscribers + members + admins)"
    elif isinstance(audience, str) and email_re.match(audience.strip()):
        emails = [audience.strip().lower()]
        label = audience.strip().lower()
    elif isinstance(audience, list):
        for x in audience:
            if isinstance(x, str) and email_re.match(x.strip()):
                emails.append(x.strip().lower())
        emails = list(dict.fromkeys(emails))  # dedupe, preserve order
        label = f"{len(emails)} recipient(s)"
    return emails, label


@app.post("/api/admin/ai/email/send")
async def admin_ai_send_broadcast(payload: AdminBroadcastIn, admin: dict = Depends(require_admin)) -> dict:
    """Confirm & send an admin-AI-drafted email. Recipients can be all newsletter subscribers,
    members, admins, everyone, or an explicit list of email addresses."""
    subject = (payload.subject or "").strip()
    html = (payload.html or "").strip()
    if not subject or not html:
        raise HTTPException(status_code=400, detail="Subject and body are required.")
    recipients, label = await _resolve_email_audience(payload.to)
    if not recipients:
        return {"ok": True, "sent": 0, "failed": 0, "message": f"No {label} to send to."}

    sent = 0
    failed = 0
    errors: list[str] = []
    for addr in recipients:
        try:
            await send_email(addr, subject, html)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(errors) < 5:
                errors.append(f"{addr}: {exc}")
    return {"ok": True, "sent": sent, "failed": failed, "total": len(recipients), "audience": label, "errors": errors}
