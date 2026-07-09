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
- 2026-02-08: **Fix: "Not an admin token" on admin save** — Axios interceptor in `frontend/src/lib/api.js` was preferring `eg_user_token` for non-`/admin` paths, so `PUT /api/site`, `/subscribers`, `/users`, `/upload`, `/ai-edit` were sent with the member token when both were present. Interceptor now forces the admin token when browser is on `/admin/*` OR when the target route is any known admin-only path. Verified with live browser test: PUT /api/site returns 200 with dual tokens in localStorage.
- 2026-02-08: **Unified Admin AI + persistence + hero controls (batch)**:
  - `GET /api/site` now returns `Cache-Control: no-store, Pragma: no-cache, Expires: 0` headers so admin edits reflect immediately across devices (fixes the "3-minute stale" bug caused by CDN caching on production).
  - New unified admin AI endpoint `POST /api/admin/ai` that auto-classifies every prompt into `chat` | `edit` | `email`. Frontend AIWriter rewritten with single input (no more Write/Edit tabs); each response is rendered with a "Reply / Site edit / Email draft" badge and appropriate action buttons.
  - Admin AI can now **broadcast to all newsletter subscribers** — it drafts subject + HTML, admin previews and confirms via `POST /api/admin/ai/email/send` (uses existing Gmail SMTP).
  - Global "AI just edited your site" undo banner on the admin dashboard listens for the `eg:ai-edit` custom event dispatched by AIWriter and shows a big Undo button until dismissed or another edit lands.
  - Hero video now has a **pause/play** button next to the mute toggle (`data-testid='hero-video-playpause'`).
  - SignupPrompt suppressed on `/admin` routes and whenever an admin token exists.
  - Testing: 8/8 backend pytest cases pass, 100% frontend flows verified (`/app/test_reports/iteration_2.json`, tests at `/app/backend/tests/test_admin_ai_unified.py`).
- 2026-02-09: **Admin 2FA (TOTP + Microsoft Authenticator) + strong password policy + master refactor**:
  - Legacy master-password-only shortcut removed. The "master" is now a real, editable, super-admin account (seeded on startup from `ADMIN_PASSWORD` env; auto-self-healed if the stored hash drifts, but only while defaults untouched).
  - All admin logins now go through the admins collection: `POST /api/admin/login` returns one of `{status: 'needs_2fa_setup', setupToken}` (first login) or `{status: 'needs_2fa', twoFactorToken}` (2FA enrolled).
  - New endpoints (`pyotp` + `qrcode`): `/admin/2fa/setup` (returns QR data URL + secret + RFC 6238 metadata), `/admin/2fa/enable` (verifies first code, issues real JWT + 10 backup codes), `/admin/2fa/login` (verifies TOTP or one-time backup code, issues real JWT), `/admin/2fa/disable` (self, requires current code), `/admin/2fa/backup-codes` + `/regenerate`, `/admin/2fa/reset/{admin_id}` (super-admin resets another admin's 2FA).
  - Purpose-scoped JWTs: `setup2fa` and `verify2fa` tokens cannot access real admin routes.
  - Strong password policy (`validate_password_strength`): min 8 chars, ≥1 uppercase, ≥1 lowercase, ≥1 digit, ≥1 symbol — enforced on `/admin/admins` create, `/admin/admins/{id}` password update, and `/auth/register`. Frontend shows a live `PasswordChecklist` under the new-admin form and blocks weak passwords in the client. `pwdIssues` + `PWD_MSG` helpers exported from `AdminLogin.jsx`.
  - AdminsManager row now shows a green "2FA on" / amber "2FA pending" badge and a "Reset 2FA" button (super-admin only, hidden for self).
  - AdminLogin.jsx handles the full 3-step flow: password → QR-code setup wizard + backup-codes screen → OR TOTP challenge — all inside one page.
  - Testing: 25/25 backend pytest cases pass, 6/6 frontend flows verified (`/app/test_reports/iteration_3.json`, tests at `/app/backend/tests/test_admin_2fa.py`).

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

## 2026-07-09 — "Edits revert" bug fixed (prices + hero video)
User reported (production): price changes and uploaded hero videos save at first, then revert.
Root causes + fixes:
1. **Admin editor race (prices reverting)**: `AdminDashboard.jsx` seeded the form from hardcoded `defaultSite` before `/api/site` resolved, so Save pushed stale defaults over the DB. Fixed: seeding gated on `!siteLoading`; dashboard also calls `refresh()` on mount.
2. **Ephemeral uploads (hero video disappearing)**: `/api/upload` wrote to local disk which production wipes on restart/redeploy. Fixed: uploads now go to Emergent object storage (records in `db.media`), `GET /api/uploads/{name}` serves from storage with 1yr immutable cache + legacy local-disk fallback. Startup migrates any legacy local files into storage.
3. **Self-heal**: `get_site_doc` now deep-merges the DB doc over `default_site()` so partial section objects can never blank out a section (preview hero had been wiped to just a kicker; now auto-healed).
Testing: iteration_4 (backend 5/5), iteration_5 (frontend race repro 1/1 PASS). Regression tests in `/app/backend/tests/test_site_and_uploads.py`.
NOTE: User must REDEPLOY to production for these fixes to take effect; hero video must be re-uploaded once on production (old file was lost from ephemeral disk).

## 2026-07-09 — Alternative 2FA methods for admin login
User asked for more 2FA options besides an authenticator app.
Delivered:
1. **Email OTP as an alternative 2FA method** — 6-digit code sent via existing Gmail SMTP; 10 min TTL; 30 s resend cooldown; max 5 wrong attempts before the code is burned; bcrypt-hashed at rest (`admin_email_otps` collection).
2. **Method chooser on every login** — after password, admin sees a card with 3 buttons: Authenticator app / Email me a code / Use a backup code. Available methods (`totp`, `email`) are computed from whether the admin has an email set.
3. **"Trust this device for 30 days"** — checkbox on all three verification screens. When ticked, backend issues a signed 30-day JWT + row in `admin_trusted_devices`; the browser stores it as `eg_admin_trust_token` and sends it on future `/api/admin/login` calls via `X-Admin-Trust-Token` header, which skips 2FA entirely and returns `status:"ok"` immediately.
4. **Trusted-device management endpoints** — `GET/DELETE /api/admin/trusted-devices` (list / revoke one / revoke all). Also auto-purged when the admin disables 2FA or a super admin resets it.
Backend testing: 18/18 pytests pass (`/app/backend/tests/test_admin_2fa_alt_methods.py`, iteration_6.json). Frontend: manual smoke screenshot only.

### Backlog (updated)
- P1: "Regenerate Backup Codes" button in Admin UI (backend endpoint exists)
- P1: "Trusted devices" list + revoke buttons in Admin UI (backend endpoints exist as of 2026-07-09; frontend page still to build)
- P2: Media Library in the admin panel (list/reuse/delete Object Storage files)
- P2: Refactor `server.py` (>2500 lines) into modular routers (auth, admin_2fa, admin_trusted_devices, cms, chat)
- P3: Retry-with-backoff on object storage GET (occasional 5xx)
