"""Mongo-backed SMS challenges, separate from email and authenticator codes."""
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from sms_service import mask_phone, require_sms_config, send_sms

TTL_MINUTES = 10
RESEND_SECONDS = 30
MAX_ATTEMPTS = 5


class PhoneCodeResponse(BaseModel):
    ok: bool = True
    sentTo: str
    expiresInMinutes: int = TTL_MINUTES
    resendAfterSeconds: int = RESEND_SECONDS


async def _send_budget(db, phone: str, now: datetime) -> None:
    # Persistent phone and global budgets also limit paid SMS pumping across routes.
    bucket = int(now.timestamp()) // 3600
    phone_key = hashlib.sha256(phone.encode()).hexdigest()
    for scope, limit in [(phone_key, 5), ("global", 100)]:
        try:
            await db.sms_send_limits.update_one(
                {"_id": f"{bucket}:{scope}", "count": {"$lt": limit}},
                {"$inc": {"count": 1}, "$set": {"expires_at": now + timedelta(hours=2)}},
                upsert=True,
            )
        except DuplicateKeyError:
            raise HTTPException(429, "Too many text requests. Please try again later or use another sign-in method.") from None


async def send_code(db, coll, key: str, phone: str, purpose: str) -> dict:
    require_sms_config()  # Fail before reserving a code or reporting success.
    now = datetime.now(timezone.utc)
    nonce = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = await asyncio.to_thread(bcrypt.hashpw, code.encode(), bcrypt.gensalt())
    try:
        await coll.update_one(
            {"_id": key, "$or": [{"sent_at": {"$lte": now - timedelta(seconds=RESEND_SECONDS)}}, {"provider": {"$ne": "twilio"}}]},
            {"$set": {"provider": "twilio", "nonce": nonce, "phone": phone,
                      "code_hash": code_hash.decode(), "ready": False, "attempts": 0,
                      "sent_at": now, "expires_at": now + timedelta(minutes=TTL_MINUTES)}},
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(429, "Please wait 30 seconds before requesting another code.", headers={"Retry-After": "30"}) from None
    try:
        await _send_budget(db, phone, now)
        sid = await send_sms(phone, f"Essential Gemstones {purpose} code: {code}. Expires in {TTL_MINUTES} minutes. Do not share this code.")
    except Exception:
        await coll.update_one({"_id": key, "nonce": nonce}, {"$set": {"ready": False}, "$unset": {"code_hash": ""}})
        raise
    result = await coll.update_one({"_id": key, "nonce": nonce}, {"$set": {"ready": True, "message_sid": sid}})
    if not result.matched_count:
        raise HTTPException(409, "This verification was cancelled. Request a new code.")
    # Twilio accepted the message; handset delivery is not guaranteed.
    return PhoneCodeResponse(sentTo=mask_phone(phone)).model_dump()


async def consume_code(coll, key: str, code: str, phone: str | None = None) -> dict | None:
    query = {"_id": key, "provider": "twilio", "ready": True,
             "expires_at": {"$gt": datetime.now(timezone.utc)}, "attempts": {"$lt": MAX_ATTEMPTS}}
    if phone:
        query["phone"] = phone
    # Reserve an attempt atomically; concurrent requests cannot exceed the limit.
    row = await coll.find_one_and_update(query, {"$inc": {"attempts": 1}}, projection={"_id": 0})
    if not row:
        return None
    clean = (code or "").strip()
    if len(clean) != 6 or not clean.isascii() or not clean.isdigit():
        return None
    if not await asyncio.to_thread(bcrypt.checkpw, clean.encode(), row["code_hash"].encode()):
        return None
    # Burn once, but keep sent_at so consuming a code does not bypass the cooldown.
    return await coll.find_one_and_update(
        {"_id": key, "nonce": row["nonce"], "ready": True, "expires_at": {"$gt": datetime.now(timezone.utc)}},
        {"$set": {"ready": False}, "$unset": {"code_hash": ""}},
        projection={"_id": 0, "phone": 1},
    )


async def revoke_admin_codes(db, admin_id: str) -> None:
    await db.admin_sms_otps.delete_one({"_id": admin_id})
    await db.admin_phone_verify.delete_one({"_id": admin_id})