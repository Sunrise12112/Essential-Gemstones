"""Persistent per-account password-attempt limits shared by server workers."""
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

WINDOW_SECONDS = 15 * 60
MAX_PASSWORD_ATTEMPTS = 10


async def check_password_attempt(db, role: str, identifier: str) -> str:
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp()) // WINDOW_SECONDS
    digest = hashlib.sha256(f"{role}:{identifier.strip().lower()}".encode()).hexdigest()
    key = f"{bucket}:{digest}"
    try:
        await db.password_attempts.update_one(
            {"_id": key, "count": {"$lt": MAX_PASSWORD_ATTEMPTS}},
            {"$inc": {"count": 1}, "$set": {"expires_at": now + timedelta(seconds=WINDOW_SECONDS * 2)}},
            upsert=True,
        )
    except DuplicateKeyError:
        wait = WINDOW_SECONDS - int(now.timestamp()) % WINDOW_SECONDS
        raise HTTPException(429, "Too many sign-in attempts. Please wait up to 15 minutes before trying again.", headers={"Retry-After": str(wait)}) from None
    return key