# 🟢 Turn On Payments — Your Simple Setup Guide

This guide gets your shop taking real money. No code, no developer console — just copy one key
and paste it into your admin. Takes about 5 minutes.

---

## Step 1 — Get your Stripe Secret key

1. Go to **https://stripe.com** and log in (or click **Start now** to create a free account).
2. Once you're in the Stripe Dashboard, look at the **top-right toggle**:
   - **Live mode** = real cards get charged, real money reaches your bank. ← use this to actually sell.
   - **Test mode** = pretend money, for practice.
   > ⚠️ **Live means real charges.** If you just want to try things first, stay in Test mode for now.
3. In the left menu (or search bar) go to **Developers → API keys**.
4. Find the **Secret key** row. It's hidden — click **Reveal** / **Reveal live key**.
   - It starts with `sk_live_` (Live) or `sk_test_` (Test).
   - ✅ Copy the **Secret key**. ❌ Do **not** use the "Publishable key" (that one starts with `pk_`).

---

## Step 2 — Paste it into your shop

1. Open your admin: go to your site and add **`/admin`**, sign in.
2. Click **Stripe Store** (top of the dashboard).
3. In the **Connect Stripe** box, paste your Secret key and click **Connect**.
4. The app checks it with Stripe. When it works you'll see a green:
   **`Connected ✓ — <Your business name> · Live · ••••ABCD`**
   (Only the last 4 characters are ever shown again — your full key stays safe on the server.)
5. If you see a red message, it usually means you pasted the Publishable key by mistake, or only part
   of the key. Re-copy the **Secret** key and try again.

That's it — your store is on. 🎉

### From now on you can, right inside the admin:
- **Products** — add, edit, price, add photos, hide/show, delete (each one is created in your Stripe account).
- **Orders** — see every paid checkout and **issue refunds**.
- **Discounts** — create codes (like `FAMILY10`) that customers type at checkout.

To swap keys later, click **Disconnect** and paste a new one.

---

## Step 3 — The full list of secrets your live site uses

Here's everything the site relies on. Most are **already set up** — you only need to handle the two marked 👉.

| What | What it's for | Do you need to do anything? |
|---|---|---|
| 👉 **Stripe Secret key** | Taking payments | **Yes — you paste it** in the Connect Stripe box (Steps 1–2 above). |
| 👉 **Allowed website addresses** (`CORS_ORIGINS`) | Lets your live web address talk to the server. **This is what's currently blocking your deploy.** | **Yes — set it once** (see below), then redeploy. |
| AI key (`EMERGENT_LLM_KEY`) | The chat assistant & AI site editor | ✅ Already set — leave as-is. |
| Email sending (`SMTP_*`) | Welcome emails, admin login codes | ✅ Already set — leave as-is. |
| Newsletter sending (`RESEND_API_KEY`) | Newsletter delivery | ✅ Already set — leave as-is. |
| Member login secret (`JWT_SECRET`) | Keeps member & admin logins secure | ✅ Already set — leave as-is. |
| Database (`MONGO_URL`, `DB_NAME`) | Stores your content, members, orders | ✅ Already set — leave as-is. |

### Fixing the "allowed website addresses" (unblocks deployment)
1. In Emergent, open your **Deployment** panel → **Secrets**.
2. Find **`CORS_ORIGINS`** and set its value to this exact list (no spaces, commas between):

   ```
   https://gemstone-makeover.emergent.host,https://essentialgemstones.com,https://www.essentialgemstones.com
   ```

   (Replace with your real live web addresses if different. Do **not** use `*`.)
3. Click save, then **Redeploy**.
   > Note: a plain redeploy without changing this value won't help — the old value sticks until you edit it here.

---

## Quick answers
- **Is my key safe?** Yes. It's stored on the server and used only to talk to Stripe. The browser never sees it again — only the last 4 digits.
- **Test before going live?** Paste a `sk_test_` key, use test card `4242 4242 4242 4242` (any future date, any CVC), then swap to your `sk_live_` key when ready.
- **Where do payouts go?** To the bank account you add inside Stripe (Stripe → Settings → Payouts).

Need a hand with any step? Just ask. 🙌
