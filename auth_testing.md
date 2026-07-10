# Google Auth (Emergent-managed) — Testing Playbook

## Test Backend Endpoint

The exchange endpoint is `POST /api/auth/google/session` with body `{"session_id": "..."}`.
It calls Emergent's session-data endpoint, upserts the user in `db.users`, and returns `{token, user}`.

To simulate the exchange without a real Google flow, seed a fake user + JWT directly:

```bash
cd /app/backend && python3 -c "
import asyncio, os, jwt
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv(Path('/app/backend/.env'))
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL']); db = c[os.environ['DB_NAME']]
    email = 'gtest@example.com'
    uid = await db.users.find_one({'email': email})
    if not uid:
        uid = {'_id': 'gtest-'+str(int(datetime.utcnow().timestamp())), 'fullName': 'Google Test', 'email': email,
               'passwordHash': '', 'authProvider': 'google', 'isBanned': False, 'favorites': [], 'picture': '',
               'createdAt': datetime.utcnow().isoformat()}
        await db.users.insert_one(uid)
    token = jwt.encode({'sub': uid['_id'], 'email': email, 'role': 'user',
        'iat': int(datetime.utcnow().timestamp()),
        'exp': int((datetime.utcnow()+timedelta(days=7)).timestamp())},
        os.environ['JWT_SECRET'], algorithm='HS256')
    print('user_id:', uid['_id'])
    print('token:', token)
asyncio.run(main())
"
```

Then verify /api/auth/me returns the user:

```bash
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
curl -s "$API/api/auth/me" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## Frontend flow to test

1. Open the app.
2. Click "Sign in" (or the account icon) → AuthModal opens.
3. Click "Continue with Google" — the browser navigates to `auth.emergentagent.com/?redirect=<origin>/`.
4. After Google approves, the page returns to `<origin>/#session_id=<sid>`.
5. `AuthCallback` synchronously detects the fragment during render, POSTs it to `/api/auth/google/session`, stores the JWT in localStorage as `eg_user_token`, sets the user in AuthContext, and cleans the URL.

## Cleanup

```bash
cd /app/backend && python3 -c "
import asyncio, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('/app/backend/.env'))
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL']); db = c[os.environ['DB_NAME']]
    r = await db.users.delete_many({'email':{'$regex':'gtest@'}})
    print('cleaned', r.deleted_count)
asyncio.run(main())
"
```
