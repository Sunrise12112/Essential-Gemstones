"""Test helper: seed a known OTP (123456) for phone / admin SMS flows. Usage: python seed_otp.py <collection> <key>"""
import os
import sys
from datetime import datetime, timedelta

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
coll, key = sys.argv[1], sys.argv[2]
db[coll].update_one(
    {"_id": key},
    {"$set": {
        "code_hash": bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "sent_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        "attempts": 0,
    }},
    upsert=True,
)
print("seeded", coll, key)
