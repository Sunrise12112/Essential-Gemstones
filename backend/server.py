"""Essential Gemstones CMS Backend with multi-admin & permissions."""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import uuid
from datetime import datetime, timedelta
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1121211221")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_DAYS = 30

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
    permissions: list[str] = []
    isSuper: bool = False


class AdminUpdate(BaseModel):
    password: Optional[str] = None
    permissions: Optional[list[str]] = None
    isSuper: Optional[bool] = None


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def make_token(sub: str, is_super: bool, permissions: list[str], username: str, role: str = "admin") -> str:
    payload = {
        "sub": sub,
        "username": username,
        "role": role,
        "isSuper": is_super,
        "permissions": permissions,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=JWT_DAYS)).timestamp()),
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
        "permissions": doc.get("permissions", []),
        "isSuper": bool(doc.get("isSuper")),
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


async def get_site_doc() -> dict:
    doc = await db.site.find_one({"_id": "main"})
    if doc is None:
        doc = {"_id": "main", **default_site()}
        await db.site.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------------- ROUTES ---------------- #


@app.get("/api/")
async def root() -> dict:
    return {"message": "Essential Gemstones API"}


@app.post("/api/admin/login")
async def admin_login(data: LoginIn) -> dict:
    # Username + password: lookup in admins collection
    if data.username:
        doc = await db.admins.find_one({"username": data.username.lower().strip()})
        if not doc or not verify_password(data.password, doc.get("passwordHash", "")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = make_token(
            sub=doc["_id"],
            is_super=bool(doc.get("isSuper")),
            permissions=doc.get("permissions", []),
            username=doc["username"],
        )
        return {"token": token, "user": doc_to_admin(doc)}

    # Legacy: master password (super admin)
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = make_token(sub="master", is_super=True, permissions=ALL_PERMS, username="master")
    return {
        "token": token,
        "user": {"id": "master", "username": "master", "isSuper": True, "permissions": ALL_PERMS},
    }


@app.get("/api/admin/me")
async def admin_me(admin: dict = Depends(require_admin)) -> dict:
    return {
        "ok": True,
        "user": {
            "id": admin.get("sub"),
            "username": admin.get("username"),
            "isSuper": bool(admin.get("isSuper")),
            "permissions": admin.get("permissions", []),
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
    if username == "master":
        raise HTTPException(status_code=400, detail="Reserved username")
    existing = await db.admins.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    perms = [p for p in (payload.permissions or []) if p in ALL_PERMS]
    if payload.isSuper:
        perms = ALL_PERMS.copy()
    doc = {
        "_id": str(uuid.uuid4()),
        "username": username,
        "passwordHash": hash_password(payload.password),
        "permissions": perms,
        "isSuper": bool(payload.isSuper),
        "createdAt": datetime.utcnow().isoformat(),
    }
    await db.admins.insert_one(doc)
    return doc_to_admin(doc)


@app.put("/api/admin/admins/{admin_id}")
async def update_admin(admin_id: str, payload: AdminUpdate, admin: dict = Depends(require_admin)) -> dict:
    require_super(admin)
    doc = await db.admins.find_one({"_id": admin_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Admin not found")
    update: dict[str, Any] = {}
    if payload.password:
        update["passwordHash"] = hash_password(payload.password)
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


# ---- uploads ---- #


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

    new_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / new_name

    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds max size of {max_bytes // (1024 * 1024)}MB",
                )
            out.write(chunk)
    return {"url": f"/api/uploads/{new_name}", "kind": kind, "size": size}


@app.get("/api/uploads/{name}")
async def serve_upload(name: str) -> FileResponse:
    safe_name = Path(name).name
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


def _send_email_sync(to_email: str, subject: str, html: str, reply_to: Optional[str] = None) -> None:
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP credentials not configured")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_USER))
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


async def send_email(to_email: str, subject: str, html: str, reply_to: Optional[str] = None) -> None:
    await asyncio.to_thread(_send_email_sync, to_email, subject, html, reply_to)


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
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
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
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(payload.password, doc.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


def _unified_admin_prompt(site_json: str, subscriber_count: int) -> str:
    schema_keys = list(default_site().keys())
    return (
        "You are the SITE OWNER'S personal AI for Essential Gemstones, a handmade lava-stone bracelet brand "
        "founded by Luca (he/him, nine years old). You act on behalf of the admin. You can hold a normal "
        "conversation, draft copy, EDIT the live site, or SEND an email broadcast to every newsletter subscriber. "
        "Choose the ONE action that best fits the admin's request.\n\n"
        "VOICE: warm, earthy, sincere, plain and grounded. Short sentences. No exclamation-heavy hype, no emojis. "
        "Never refer to Luca as she/her/they. Never lead descriptions of Luca with his age.\n\n"
        "OUTPUT FORMAT: Reply with ONLY a single JSON object (no prose outside JSON, no code fences). Exact shape:\n"
        "{\n"
        '  "kind": "chat" | "edit" | "email",\n'
        '  "reply": "<what to show the admin>",\n'
        '  "edits": [ {"path": "<dotted path>", "value": <new value>} ],\n'
        '  "email": { "subject": "<subject line>", "html": "<well-formatted HTML body>" }\n'
        "}\n"
        "Only include 'edits' when kind='edit'. Only include 'email' when kind='email'. 'reply' is ALWAYS required.\n\n"
        "WHEN TO PICK EACH kind:\n"
        "- 'chat'  \u2192 the admin is asking a question, brainstorming, or wants you to draft copy without applying it. "
        "Put the draft or answer in 'reply'.\n"
        "- 'edit'  \u2192 the admin wants a live change to the website (hero, products, FAQ, colors of copy, section order, "
        "visibility, footer, etc.). Fill 'edits' with MINIMAL, TARGETED paths and put a one-sentence summary in 'reply'.\n"
        "- 'email' \u2192 the admin wants a message sent to newsletter subscribers "
        f"(current subscriber count: {subscriber_count}). "
        "Write a real, warm HTML email in 'email.html' using inline styles suitable for email clients. Put a short "
        "confirmation in 'reply' like: 'Ready to send to your subscribers. Say \"send it\" to confirm.' "
        "IMPORTANT: Only pick kind='email' when the admin's message clearly says they want to email/broadcast/send-a-newsletter to subscribers.\n\n"
        "EDIT PATH SYNTAX:\n"
        "- Dot notation to descend into objects. Bracket [n] to select an array index. "
        "Example: products.items[0].description, sectionVisibility.faq, sectionOrder.\n"
        "- To replace an entire array, set path to the array key and value to the new array.\n"
        f"- Top-level keys you may edit: {schema_keys}.\n\n"
        "RULES:\n"
        "- Do EXACTLY what the admin asked \u2014 no more, no less. Do not rewrite unrelated fields.\n"
        "- Preserve existing structure. Do not remove keys the site uses. Never invent fields the schema doesn't have.\n"
        "- If the request is unsafe/impossible, set kind='chat' and explain in 'reply'.\n\n"
        "CURRENT SITE CONTENT (JSON):\n" + site_json
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
    system_prompt = _unified_admin_prompt(site_json, subscribers_count)

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

    # --- Handle EMAIL BROADCAST ---
    elif kind == "email":
        email_obj = parsed.get("email") or {}
        subject = str(email_obj.get("subject") or "").strip()
        html = str(email_obj.get("html") or "").strip()
        if not subject or not html:
            result["kind"] = "chat"
            result["reply"] = (reply_text or "") + "\n\n(I didn't have a subject/body ready \u2014 tell me what to say and I'll draft it.)"
        else:
            # Draft-only: return the draft; admin confirms via /api/admin/ai/email/send
            result["emailDraft"] = {"subject": subject, "html": html, "recipientCount": subscribers_count}
            if not reply_text:
                result["reply"] = f"Draft is ready \u2014 preview below. Say 'send it' to broadcast to {subscribers_count} subscriber(s)."

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


@app.post("/api/admin/ai/email/send")
async def admin_ai_send_broadcast(payload: AdminBroadcastIn, admin: dict = Depends(require_admin)) -> dict:
    """Confirm & send an admin-AI-drafted broadcast to every newsletter subscriber."""
    subject = (payload.subject or "").strip()
    html = (payload.html or "").strip()
    if not subject or not html:
        raise HTTPException(status_code=400, detail="Subject and body are required.")
    subs: list[str] = []
    async for doc in db.subscribers.find():
        e = (doc.get("email") or "").strip().lower()
        if e:
            subs.append(e)
    if not subs:
        return {"ok": True, "sent": 0, "failed": 0, "message": "No subscribers to send to."}

    sent = 0
    failed = 0
    errors: list[str] = []
    for addr in subs:
        try:
            await send_email(addr, subject, html)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(errors) < 5:
                errors.append(f"{addr}: {exc}")
    return {"ok": True, "sent": sent, "failed": failed, "totalSubscribers": len(subs), "errors": errors}
