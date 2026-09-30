# Essential Gemstones — PRD

> **2026-06 update**: Added clickable "Built by Nano AI" credit (links to nano-ai.org) to all AI surfaces — customer chat widget (`ChatBubble.jsx`), and the Admin AI panel/site editor (`AIWriter.jsx`). Also replaced the stale "Claude" badge in the Admin AI header with a "Nano AI" link.


## Original Problem Statement
Recreate essentialgemstones.com pixel-perfectly with an artisan, earthy aesthetic. Full CMS admin for content editing, multi-admin support with permissions, Gmail SMTP newsletter subscription, Hero video with tap-to-unmute, member accounts/auth with VIP perks and favorites, Claude-powered AI chat widget, Admin AI Site Editor, and per-user persistent chat memory.

## Stack
- Frontend: React (CRA), Tailwind CSS, shadcn/ui, lucide-react
- Backend: FastAPI + Motor (MongoDB async)
- Auth: JWT (separate roles for users and admins), bcrypt via passlib
- Email: Gmail SMTP (hello@essentialgemstones.com)
- AI: `emergentintegrations` with `claude-sonnet-4.5` via EMERGENT_LLM_KEY
- SMS: Twilio Programmable Messaging (configuration-ready; credentials/sender not yet available), with `phonenumbers` for number-only E.164 input. No carrier gateways or VoIP blocking.

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

## 2026-07-09 (6) — Resend email integration
User asked: add Resend to the app for better email deliverability.
Delivered:
1. **`send_email()` now prefers Resend, falls back to Gmail SMTP** — same signature, so every existing caller (newsletter welcome, admin notifications, admin AI broadcasts, admin 2FA email OTP, contact form) works unchanged. If `RESEND_API_KEY` is set the app sends via Resend; if that call throws for any reason we automatically retry via the existing Gmail SMTP path so email never breaks. If both fail, we raise a combined error.
2. Env vars added to backend/.env: `RESEND_API_KEY`, `RESEND_FROM` (defaults to `onboarding@resend.dev`).
3. `resend>=2.0.0` pinned in `requirements.txt`.
Verified: `POST /api/subscribe` returns `welcomeSent: true` end-to-end through the new Resend path.

**Known limitation on the free Resend sandbox** — on the shared `onboarding@resend.dev` sender, Resend will only deliver to the email address the account was created with. To send to real customers/subscribers the user must verify their own domain (essentialgemstones.com) at resend.com/domains, then flip `RESEND_FROM` to `hello@essentialgemstones.com`. Until then, any recipient other than the Resend account owner will bounce (the fallback to Gmail SMTP catches this).

## 2026-07-09 (5) — Sign in with Google (Emergent-managed OAuth)
User asked: add Google sign-in to the app.
Delivered:
1. **Frontend "Continue with Google" button** on the AuthModal (both Sign In and Create Account modes), sitting above the email/password form with a divider. Uses `window.location.origin + '/'` for the redirect (never hardcoded).
2. **AuthCallback component** at `/app/frontend/src/components/auth/AuthCallback.jsx` renders when `location.hash` contains `session_id=`. Synchronously checked during App render (not useEffect) to avoid race conditions per the playbook. Uses a `useRef` guard so StrictMode double-mount doesn't burn the session_id twice.
3. **AuthProvider race-condition fix** — the `/auth/me` refresh call is skipped when the URL fragment contains `session_id=` so AuthCallback can exchange the code and mint a JWT first.
4. **Backend `POST /api/auth/google/session`** — takes `{session_id}`, calls Emergent's `/session-data` endpoint server-side (never from the frontend), upserts the user in `db.users` by email (auto-creates a Google-only account if new, or logs into an existing email account, refreshing name + profile picture), and returns our normal `{token, user}` shape. Existing endpoints (`/auth/me`, favorites, waitlist, etc.) work unchanged.
5. `user_to_public` now returns `picture` + `authProvider` fields.
6. **Admin auth is completely untouched** — separate `db.admins` collection with TOTP/Email OTP/trusted devices continues to work as before.

Verified: missing session_id → 422 pydantic error; bogus session_id → friendly 401 "This Google sign-in link has expired. Please try again."; screenshot confirms the Google button renders correctly in the modal.

## 2026-07-09 (4) — Product detail modal + waitlist
User asked: clicking a product should open an enlarged view with Buy Now, description, add-to-waitlist, and more.
Delivered:
1. **ProductModal** (`/app/frontend/src/components/ProductModal.jsx`) — full-screen modal that opens on click of any product card. Includes: large image (with gallery-dot navigation if a `gallery` array is on the product), badge, price, short description, optional `longDescription`, optional `details`/`features` bullet list, trust row (handmade · real stones · ships in 3–5 days), Buy Now CTA (or "Currently unavailable" placeholder), favorite heart, and "Notify me" waitlist (email input for guests, one-click for logged-in members). ESC + arrow-key navigation + click-outside-to-close + body-scroll lock.
2. **Waitlist backend** — new collection `product_waitlist` and four endpoints:
   - `POST /api/products/{id}/waitlist` (guest via email or authed user), idempotent
   - `DELETE /api/products/{id}/waitlist` (authed only)
   - `GET /api/me/waitlist` (authed users see their own list)
   - `GET /api/admin/waitlist` (admin sees everyone waiting for what)
3. Products.jsx made the whole card clickable/keyboard-accessible with a hover "View details" hint; the Heart + Buy Now buttons stop propagation so they still work in isolation.
Verified: curl create/idempotent/empty-email/invalid-product all correct; live screenshot confirms modal opens on card click and renders all sections.

## 2026-07-09 (3) — AI can PREVIEW the site + SEND EMAILS to anyone
User asked: (a) let the AI show a live preview of the site, (b) let the AI send emails to any recipient — not just newsletter subscribers.
Delivered:
1. **New `kind:"preview"` action** — AI responds with `preview:{section, anchor, note}` and the AIWriter renders an embedded iframe pointing to the live site at the requested section anchor (`top`,`shop`,`faq`,`story`,`founder`,`members`,`chakra`, or `full`). Refresh + open-in-new-tab buttons included.
2. **Emails to anybody** — `POST /api/admin/ai/email/send` now accepts a `to` field: a list of email addresses, a single email string, or one of the audience keywords `subscribers` (default), `members`, `admins`, `all`. New helper `_resolve_email_audience` handles the resolution and de-duping.
3. **Editable recipients in the email draft UI** — the EmailDraftCard shows audience buttons (Newsletter / Members / Admins / Everyone / Specific people) plus a free-form recipient list. Admin picks who gets the message before hitting "Send".
4. AI prompt updated so Claude picks `kind:"preview"` for "show me the hero" style requests and correctly populates `email.to` with the specific address(es) mentioned in the conversation.

Verified end-to-end via curl + a real AI round-trip: "Show me the hero" \u2192 `kind:preview, anchor:top`; "Draft an email to grandma@example.com" \u2192 `kind:email, to:['grandma@example.com']`.

## 2026-07-09 (2) — Email required for admins + Admin AI can manage admins
User asked: (1) email is required when creating a new admin, (2) super admins can edit any admin's email, (3) the Admin AI can create/edit/delete/reset admins (super-admin only).
Delivered:
1. `AdminCreate.email` is now `EmailStr` (required). POST `/api/admin/admins` rejects missing/invalid emails and duplicates.
2. PUT `/api/admin/admins/{id}` validates email format and duplicates; super admins can edit anyone's email, others can only edit their own.
3. AdminsManager UI: required email input on create form; pencil-icon inline edit for email on every row.
4. Admin AI (`POST /api/admin/ai`) now supports `kind:"admins"` with a full `_apply_admin_action` dispatcher: `create` / `update` / `delete` / `resetPassword` / `reset2fa`. Restricted to super admins — non-super callers get a chat fallback.
5. When the AI is asked to create an admin without a password, a strong 14-char password is auto-generated and returned in `adminAction.generatedPassword` so the super admin can share it once. Generator is guaranteed to satisfy the password policy (fixed after testing agent found ~11% failure rate on first pass).
6. AIWriter component renders the new admin-action result card (target admin details + temporary-password banner). AdminsManager auto-refreshes on `eg:admin-managed` window event.
Backend testing: **24/24 pytests pass**, previously flaky password-generator test now 5/5 passes after fix (`/app/backend/tests/test_admin_management.py`, iteration_7.json).

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

## 2026-06 — OG / Social Share Meta
- index.html: title "Essential Gemstones", description "Handmade · Volcanic · Intentional", og:*/twitter:* tags with user-supplied 7-chakra lava bracelet image (hosted on customer-assets; local copy at frontend/public/og-image.jpg). Requires redeploy to reflect on live site.

## 2026-09-25 — Number-only Twilio SMS authentication
Latest user request: “You can use twillio for phone add it now and make it so it will accept a Google Voice number And it does not require you to choose your carrier you just put in your phone number”. User approved checking existing configuration and explicitly requested no further questions.

### Implemented
- Replaced carrier email-to-text gateways with official Twilio **Programmable Messaging**, not Verify. Removed carrier selectors, carrier-list endpoint, and carrier fields from new member/admin phone API payloads. Member phone registration and sign-in begin with the phone number alone.
- Added `backend/sms_service.py` (Twilio transport, E.164 validation without carrier/line-type lookups, nonblocking bounded network calls, sanitized failures) and `backend/sms_otp.py` (MongoDB code lifecycle). Installed `twilio==9.11.1` and `phonenumbers==9.0.40` through pip and saved dependencies.
- Google Voice/VoIP numbers are accepted by app validation. Their actual receipt of automated SMS remains subject to Twilio, Google Voice, and carrier restrictions; it is NOT guaranteed.
- Codes are bcrypt-hashed, expire in 10 minutes, allow five attempts, and are atomically single-use. Atomic 30-second resend cooldown, five texts/number/hour and 100 texts globally/hour, with persistent MongoDB counters and TTL cleanup. Failed sends cannot be verified. Legacy carrier-gateway challenges are not accepted.
- Preserved existing phone-account IDs/favorites by looking up old ten-digit numbers and normalizing them after successful sign-in. Banned accounts remain blocked.
- Admin phone enrollment binds the pending number to its verification code. SMS challenge availability requires a verified phone, not a carrier. Removing/replacing the phone and resetting/disabling 2FA revoke pending SMS challenges. Existing TOTP/email/backup/trusted-device methods remain supported.
- Fixed nested forms in the member auth modal, added scroll-safe mobile sizing and deterministic mobile navigation/auth controls, and preserved email/Google sign-in. Admin SMS errors no longer imply a code was sent; email and SMS cooldowns are independent. Added admin phone-section toggle/content test IDs and accessibility state.
- Addressed authentication testing findings: `backend/auth_throttle.py` limits password attempts per normalized account/role to 10 per 15-minute window, resets on success; removed JWT_SECRET/ADMIN_PASSWORD fallback secrets; CORS now uses explicit environment-configured origins rather than wildcard+credentials. Preview ingress rewrites its origin to a specific proxy hostname, also explicitly listed in CORS_ORIGINS. No supervisor changes were necessary.
- Temporary browser test account and seed helper removed after verification; no existing master credentials/enrollment changed.

### Status / blocking configuration
**Twilio credentials were NOT found. Live SMS is NOT activated and Google Voice receipt has NOT been verified.** No runtime mock, fake code, or email-gateway fallback exists. Send endpoints correctly return an explanatory 503 instead of claiming success.

Required backend config: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and exactly one of `TWILIO_PHONE_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`. `DEFAULT_PHONE_REGION=US` is configured. Trial recipient restrictions and applicable US sender verification/A2P requirements still apply. Details: `/app/memory/SMS_SETUP.md`.

### Verification
- Reports: `/app/test_reports/iteration_8.json`, `/app/test_reports/iteration_9.json`.
- Final self-rerun: **27/27 targeted backend tests passed**, 48.77 seconds. `/app/test_reports/pytest/pytest_sms_final.xml`, `/app/test_reports/sms-final-tests.log`.
- Positive SMS transport/OTP route tests use **TEST-ONLY MOCKS** and isolated MongoDB databases. This does not establish real SMS receipt.
- Browser checks passed for mobile 320px menu/sign-in/join, no carrier/name fields, safe missing-config error, no accidental email-form requests, admin SMS challenge error + backup fallback, and tablet/desktop auth layouts. Admin setup send/remove error UI also tested with **TEST-ONLY MOCKED responses**.
- Python compilation and frontend build pass (pre-existing lint/deprecation warnings only). Final phone-section selector/accessibility change verified by rendering both open/closed states. Temporary database fixtures cleaned.
- Full real Google OAuth sign-in and live SMS delivery were not exercised; invalid Google session and existing email/password/admin alternatives were checked.

### Current priorities (supersedes older roadmap entries)
- **P0 — Activation blocker:** Twilio account credentials and an approved SMS sender are needed before real phone auth can send texts. Then verify one member and one admin code to an opted-in Google Voice number end-to-end.
- **P0 — Before further complex features:** continue modularizing `server.py` (>3,000 lines); SMS transport, OTP lifecycle and password throttling have now been extracted.
- **P1 — User verification:** previous production AI authentication issue remains outside this SMS task; no new report investigated here.
- **P1 — Account recovery UI:** regenerate backup codes; trusted-device list/revoke controls (backend exists).
- **P2:** attach guest waitlists by email on sign-in; media library; evaluate httpOnly session storage as a separate architectural change, not an SMS regression.
- **Future enhancement:** opt-in waitlist text alerts using the same verified number after real SMS delivery is active.

## 2026-06 — Stripe checkout + Nano AI section + SMS removal + mobile pass
User pivot: "Remove all the SMS stuff, add Stripe integration for all products." Plus: add an editable "Nano AI" homepage section (content pulled from https://nano-ai.org), and optimize for mobile.

### Delivered
1. **SMS/Twilio fully removed.** Deleted `sms_service.py`, `sms_otp.py`, `PhoneAuthForm.jsx`, `AdminPhoneSetup.jsx`. Stripped all phone/SMS code from `server.py` (member phone login, admin SMS 2FA, phone verify endpoints, phone fields in `doc_to_admin`/`user_to_public`, SMS TTL indexes), `AuthModal.jsx`, `AuthContext.jsx`, `AdminLogin.jsx` (SMS step/method), `AdminDashboard.jsx` (phone section). Admin 2FA now TOTP + Email OTP + backup codes only. `/api/auth/phone/*` and `/api/admin/2fa/sms/send`, `/api/admin/me/phone` return 404.
2. **Integrated per-product Stripe Checkout** (raw `stripe` SDK, existing sandbox keys in backend/.env). New endpoints: `POST /api/payments/checkout` {product_id, origin_url} → creates a Checkout Session from the admin-set DB price (inline `price_data`, `_price_to_cents` parses "$28.00"→2800), inserts `payment_transactions`, returns checkout_url; `GET /api/payments/status/{session_id}` (with Stripe fallback poll); `POST /api/stripe/webhook`. Frontend `startProductCheckout` (lib/api.js): Buy Now on Products.jsx + ProductModal.jsx. **Per-product `buyUrl` acts as an OPTIONAL external Stripe-link override** — if set, opens that link; else built-in checkout. The 2 seeded products keep their existing buy.stripe.com links. New pages `/payment/success` (polls status) + `/payment/cancel`. Tax mode: DIY (Stripe just processes; no tax) — can switch to Stripe-calculates or Stripe-manages-all later.
3. **Nano AI section** — new `nanoAI` in default_site + SiteContext + SECTION_PERMS + sectionOrder/visibility. `NanoAI.jsx` (dark earthy section) registered in Home. Fully editable in AdminDashboard ("Meet Nano AI" card: kicker/title/subtitle/button/note/image/features). `get_site_doc` now reconciles sectionOrder/visibility so newly-added sections always appear even on older saved docs. Home.jsx appends any registered section missing from a saved order.
4. **Mobile pass** — global `overflow-x:hidden`, responsive Hero (H1 text-4xl→7xl, padding, quote card repositioned), verified single-column product grid, hamburger nav, chat widget all fine at 390px. No horizontal overflow.
5. **Setup guide** for the user at `/app/STRIPE_SETUP.md` (super simple, plain-English Stripe instructions incl. test card 4242…).

### Verification
- iteration_10.json: 8/8 backend pytest pass, frontend 100%. Regression tests: `/app/backend/tests/test_stripe_nanoai_no_sms.py`. Checkout verified (chakra $28→2800, 404 on bad product, SMS endpoints 404, TOTP 2FA works, nanoAI CRUD+render, mobile no overflow).
- STRIPE MODE = test sandbox (already provisioned, keys in backend/.env). User must claim the sandbox + complete KYC to go live.

## 2026-06 (2) — Stripe switched to BYOK + full admin Stripe management
Context: the Emergent claimable sandbox was UNLINKED by the user. Dead sandbox secrets removed from backend/.env (STRIPE_SECRET_KEY/PUBLISHABLE/ACCOUNT_ID/WEBHOOK_SECRET/MODE). Stripe now uses **BYOK** via runtime env `STRIPE_API_KEY` (platform injects `sk_test_emergent` placeholder; user adds their real `sk_test_`/`sk_live_` key via Emergent Payments/Secrets panel). Backend treats `""`/`sk_test_emergent` as "not connected".

### Delivered (admin panel = source of truth, pushes to Stripe)
- New admin page **/admin/stripe** (`StripeProducts.jsx`, linked from dashboard header "Stripe Store"): tabs Products / Orders / Discounts. Shows a "Connect your Stripe account" screen until a real key is set.
- Backend (raw `stripe` SDK, keyed by STRIPE_API_KEY, all `require_admin`): `GET/POST/PUT/DELETE /api/admin/stripe/products` (create Product+Price, price change makes a new default price, delete→archive fallback, images, active toggle); `GET /api/admin/stripe/payments` (orders) + `POST /api/admin/stripe/refund`; `GET/POST/DELETE /api/admin/stripe/coupons` (Coupon+PromotionCode). Public `GET /api/stripe/catalog` (active products) drives the storefront when Stripe is connected (falls back to CMS products otherwise). `POST /api/payments/checkout` now takes `price_id` (Stripe catalog) or `product_id` (CMS fallback) and enables `allow_promotion_codes`. Webhook moved to `/api/webhook/stripe` (BYOK convention), signature optional.
- Storefront `Products.jsx` loads `/stripe/catalog` and renders Stripe products (Buy Now → checkout by price_id) when connected.

### Verified
- Admin TOTP login works; `/admin/stripe/status` → `{configured:false}`; product endpoints → 503 "not connected" (graceful); frontend compiles; checkout CMS-fallback path works.
- **NOT E2E-verifiable here:** product/refund/coupon CRUD needs the user's real Stripe key (the shared `sk_test_emergent` placeholder can't hit api.stripe.com via the raw SDK). Once STRIPE_API_KEY is a real key, the admin page activates fully.

### Deployment note (2026-06)
- Production deploy failed: the deployed **CORS_ORIGINS secret** is `*`/placeholder, rejected by the server guard (server.py ~2302). FIX (user): Deployment Panel → Secrets → set `CORS_ORIGINS` to an explicit list (e.g. `https://gemstone-makeover.emergent.host,https://essentialgemstones.com,https://www.essentialgemstones.com`), then redeploy. Previous healthy deploy stays live. Guard is intentional — do NOT allow `*` with credentials.

## 2026-06 (3) — Connect Stripe from the admin (paste key)
- New **Connect Stripe** box on /admin/stripe: admin pastes Stripe Secret key; backend validates via stripe.Account.retrieve(api_key=...) and stores it server-side in db.app_settings (_id:"stripe"). Key never returned to browser — only business/mode/last4 shown. Disconnect button clears it.
- Per-request key resolution: _stripe_on() loads DB key (fallback env STRIPE_API_KEY, ignoring sk_test_emergent placeholder) into the SDK before every Stripe call (multi-pod safe).
- Endpoints: POST /api/admin/stripe/connect, POST /api/admin/stripe/disconnect; GET /api/admin/stripe/status returns business/mode/last4.
- STRIPE_SETUP.md rewritten (get Live key -> paste -> full secrets table incl CORS_ORIGINS deploy fix).
- Verified via curl: bad pk_ key ->friendly 400; fake sk_ ->stripe rejected 400; status not configured; frontend compiles. NOT verifiable here: successful connect with a real valid key.

## 2026-06 (4) — ALL Stripe removed (user pivot)
- User hit a failed coupon delete (restricted-key symptom) and decided to drop Stripe entirely.
- Removed: import stripe; whole Stripe block in server.py (checkout, status/catalog/webhook, connect/disconnect, products/orders/refunds/coupons CRUD, all helpers); frontend StripeProducts.jsx, PaymentSuccess.jsx, PaymentCancel.jsx + their routes; startProductCheckout in lib/api.js; Stripe Store link in admin; STRIPE_SETUP.md; test_stripe_nanoai_no_sms.py.
- Buy model reverted to the simple per-product manual link: admin pastes any URL (Stripe/PayPal/Etsy/etc.) into the product "Buy link" field; Buy Now / Buy now opens it in a new tab. Blank = no Buy button ("Tap for details").
- Verified: backend healthy, /api/stripe/catalog and /api/payments/checkout now 404; /api/site returns 2 products + nanoAI; frontend compiles (only pre-existing exhaustive-deps warning); homepage renders.

## 2026-06 (5) — AI switched from Claude to Nano AI (owner's own API)
- All three AI features now call the Nano REST API (POST https://nano-ai.org/functions/nano-api, x-api-key header, name + model fields) instead of Claude/Emergent LLM.
- Config in backend/.env: NANO_API_KEY, NANO_API_URL, NANO_MODEL=claude_sonnet_4_6. Helper _nano_generate() (httpx, 90s timeout, friendly 401/403/timeout errors); _nano_name_from_request / _nano_admin_name supply Nano the person name (member fullName / admin username).
- /api/chat/stream (Chat with Luca): calls Nano, streams the reply word-by-word over SSE (same event contract, no frontend change); persists meta.nanoChatId per session so Nano keeps thread memory.
- /api/admin/ai (Admin AI): Nano-powered; still parses JSON actions (kind/reply). Chat works; EDIT actions are BEST-EFFORT/unreliable (Nano sometimes says it edited but returns applied=[]) — accepted tradeoff per user choice.
- /api/admin/ai-edit (AI site editor): Nano reliably returns our JSON edit plan and applies it (verified: hero.kicker edit applied).
- Removed emergentintegrations.llm.chat import/usage. EMERGENT_LLM_KEY still used for object storage only.
- DEPLOY: add NANO_API_KEY (and NANO_API_URL, NANO_MODEL) to Deployment -> Secrets so live site uses Nano. Nano API needs the Max plan (403 otherwise). Verified all 3 in preview.
