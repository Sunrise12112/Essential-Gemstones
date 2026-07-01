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
META_PERMS = ["sectionOrder", "sectionVisibility", "manage_admins", "manage_subscribers"]
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


def make_token(sub: str, is_super: bool, permissions: list[str], username: str) -> str:
    payload = {
        "sub": sub,
        "username": username,
        "isSuper": is_super,
        "permissions": permissions,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=JWT_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def require_admin(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
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
async def get_site() -> dict:
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
