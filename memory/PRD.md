# Essential Gemstones — PRD

## Original Problem Statement
Recreate essentialgemstones.com pixel-perfectly with an artisan, earthy aesthetic. Full CMS admin for content editing, multi-admin support with permissions, Gmail SMTP newsletter subscription, Hero video with tap-to-unmute, member accounts/auth with VIP perks and favorites, Claude-powered AI chat widget, Admin AI Site Editor, and per-user persistent chat memory.

## Stack
- Frontend: React (CRA), Tailwind CSS, shadcn/ui, lucide-react
- Backend: FastAPI + Motor (MongoDB async)
- Auth: JWT (separate roles for users and admins), bcrypt via passlib
- Email: Gmail SMTP (hello@essentialgemstones.com)
- AI: `emergentintegrations` with `claude-sonnet-4.5` via EMERGENT_LLM_KEY

## Implemented (chronological)
- 2026-02: Full site UI replicating essentialgemstones.com
- 2026-02: CMS backend + admin UI to edit every text/media section
- 2026-02: Multi-admin auth with granular permissions
- 2026-02: Hero video with tap-to-unmute overlay
- 2026-02: Gmail SMTP newsletter subscribe + mailto contact
- 2026-02: Member auth (register/login/favorites/VIP area)
- 2026-02: AI Chat widget (public modes: ask-luca, stone-guide) via Claude Sonnet 4.5
- 2026-02: Admin AI Site Editor (admin-writer mode)
- 2026-02: Per-user + per-admin persistent chat session memory (create/list/rename/delete)
- 2026-02: Shopping cart removed at user request
- 2026-02-08: **AI Chat locked behind member auth** — public chat modes now require a valid user or admin JWT. Anonymous X-Client-Id requests are rejected with HTTP 401. Frontend shows a "Members only" login gate with Signup/Login CTAs. All chat session CRUD endpoints require member auth. Admin-writer path unchanged.

## Key API Endpoints
- Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/favorites/{id}`
- Admin: `POST /api/admin/login`, admin CMS + user management
- Chat (member-only): `POST /api/chat/stream`, `GET /api/chat/sessions`, `GET/PUT/DELETE /api/chat/session/{id}`
- Admin chat: `GET /api/admin/chat-sessions`, `DELETE /api/admin/chat-sessions/{id}`
- Newsletter: `POST /api/subscribe`
- CMS: `GET /api/site`, admin-guarded PUT/PATCH endpoints

## DB Collections
- `site_data`, `admins`, `users`, `subscribers`, `chat_sessions`

## Backlog / Roadmap
- P2: Split `server.py` (~1600 lines) into modular routers (`routes/auth.py`, `routes/chat.py`, `routes/cms.py`, `routes/admin.py`)
- P2: Surface a health signal when chat message persistence fails (currently silent try/except)
- P2: Cache resolved member key in request state to avoid decoding JWT twice inside `chat_stream`
- P3: Reposition "Made with Emergent" badge or chat bubble to avoid visual overlap in bottom-right

## Test Credentials
See `/app/memory/test_credentials.md`

## Test Reports
- `/app/test_reports/iteration_1.json` — 17/17 backend + 100% frontend pass on chat auth gating
- pytest suite: `/app/backend/tests/test_chat_auth.py`
