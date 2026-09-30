# Connect Stripe From the Admin Panel + Full Setup Guide

A "Connect Stripe" box in the admin where the owner pastes their Stripe key once and the whole store turns on.
Plus a plain-English written guide covering how to get that key and every other secret the live site needs.

## Who it's for
The shop owner (a non-technical admin). They want to accept real payments without touching code, config files, or a developer console — just paste one key and follow a simple written guide.

## Core features and experience
- **Connect Stripe box** on the existing "Stripe Store" admin page:
  - A single field to paste the Stripe **Secret key**, and a "Connect" button.
  - On connect, the app checks the key with Stripe. If it's wrong, a friendly message explains what to fix.
  - When it works, the box shows a green **"Connected ✓"**, the **business name** pulled from the Stripe account, whether it's **Live or Test**, and the **last 4 characters** of the key.
  - A **Disconnect** button removes the key and switches the store back off.
  - The full key is never shown again after pasting — only the last 4 are ever displayed.
- **Everything else already built runs off this key**: creating/editing/deleting products, viewing orders, issuing refunds, and creating discount codes — all against the owner's real Stripe account.
- **Written setup guide (Markdown)** that covers, in numbered click-by-click steps:
  1. Creating/opening a Stripe account and finding the **Live Secret key** (with a plain warning that Live means real cards are charged).
  2. Pasting that key into the Connect Stripe box and confirming "Connected ✓".
  3. A **complete list of every secret the live site uses** — what each is for, and whether it is already set up or the owner must provide it. This includes the one item currently blocking deployment (the allowed-website-addresses setting) with the exact value to use, plus the items already configured (AI, email sending, member logins, database) noted as "leave as-is".

## User flow
1. Owner opens the admin → "Stripe Store" page.
2. Sees the Connect Stripe box (store is "not connected" until a key is added).
3. Follows the written guide to copy their Stripe Live Secret key.
4. Pastes it, clicks Connect. The app verifies it and shows "Connected ✓ — <Business name> · Live · ••••ABCD".
5. Owner adds products, sees orders, issues refunds, and creates discount codes — all live.
6. If they ever need to swap keys, they click Disconnect and paste a new one.

## UI/UX feel
Matches the current admin: warm cream/earth tones, rounded cards, serif headings. The Connect box is reassuring and beginner-friendly — short sentences, one clear action at a time, green success state, and gentle red error messages that say exactly what to do next. The guide reads like a friendly checklist, not technical docs.

## Implementation phases
**Phase 1 — MVP (built now)**
- Connect Stripe box: paste key → verify with Stripe → store securely → show Connected state (business name, Live/Test, last 4) + Disconnect.
- All existing Stripe Store features (products, orders, refunds, discounts) and the storefront checkout use the pasted key.
- The written Markdown setup guide covering getting the Live key, connecting it, and the full list of all needed secrets (including the deployment fix and the already-set ones).

**Phase 2 — Guided go-live checks (later)**
- The page flags what's still missing before selling (e.g. "no products yet", "add a business name in Stripe"), and a one-click "make a test purchase" helper.

**Phase 3 — After-sale automation (later)**
- Automatic order-receipt emails to the owner and buyer on each paid order, and a simple sales overview (today's revenue, best sellers).

## Assumptions
- The pasted key is stored on the server side (in the app's database), used only by the backend to talk to Stripe, and never sent back to the browser or shown again — only the business name and last 4 are displayed.
- The owner starts with a **Live** key (real charges), per the choice made; the guide warns about this and notes a Test key can be pasted the same way if they want to trial first.
- The Connect Stripe box lives on the existing `/admin/stripe` page and replaces the current "add it in the Secrets panel" instructions.
- Only a signed-in admin can connect or disconnect Stripe.
- "All needed secrets" in the guide means: the Stripe key (owner provides via the panel), the allowed-website-addresses setting that currently blocks deployment (owner sets in the deployment settings, exact value provided), and the already-configured items (AI key, email/SMTP, newsletter sending, member-login secret, database) which are listed as "already set — don't change".
- Disconnecting removes the stored key immediately and the storefront falls back to the built-in CMS product list until a key is connected again.
- The guide is delivered as a single Markdown file in the project the owner can read; no in-app help screen is built (per the choice of "document only").
