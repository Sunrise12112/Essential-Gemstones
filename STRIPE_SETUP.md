# 💳 How Payments Work on Your Site (Super Simple Guide)

Your shop now takes payments with **Stripe** — the same secure system used by millions
of stores. Every product has a **"Buy Now"** button. When a customer taps it, they go to
a safe Stripe page, pay with their card, and come back to a "Thank you" page. You get the money. 🎉

You do **not** need to touch any code. Here's everything you need to know.

---

## ✅ What's already done for you
- Stripe is connected to your site (test mode for now).
- Every product with a price shows a **Buy Now** button automatically.
- Customers see a "Thank you" page after paying and a "No worries" page if they cancel.

## 🧪 Try it right now (test mode)
1. Open your website and click **Buy Now** on any product.
2. On the Stripe page, use this fake test card:
   - **Card number:** `4242 4242 4242 4242`
   - **Expiry:** any future date (e.g. `12/34`)
   - **CVC:** any 3 numbers (e.g. `123`)
   - **ZIP:** any 5 numbers (e.g. `12345`)
3. Click pay — you'll land on the "Thank you" page. That's a full test purchase!

> Test mode uses fake money. No real cards are charged until you switch to live mode (Step below).

---

## 💵 How to change a product's price
1. Go to **yoursite.com/admin** and sign in.
2. Open **Collection (Products)**.
3. Change the **Price** box (for example `$28.00`).
4. Click **Save changes**.

That new price is exactly what the customer pays at checkout. Simple as that.

> Tip: Use a normal price like `$28.00` or `$28`. The Buy Now button needs at least $0.50.

---

## 🔗 Optional: use your own Stripe payment link instead
If you'd rather make a payment link yourself inside Stripe:
1. In the product editor there's an **"Optional Stripe payment link"** box.
2. Paste a link that starts with `https://buy.stripe.com/...`
3. Save. That product's Buy Now button will now open your link instead of the built-in checkout.

Leave the box empty to use the built-in checkout (recommended — it uses the price you set).

---

## 🚀 Going live (accepting real money)
When you're ready to accept real payments:
1. Ask your Emergent builder to help you **claim your Stripe account** (one click on a link Stripe emails you).
2. Fill in your details with Stripe (name, bank account for payouts) — this is called KYC.
3. Once Stripe approves you, your site automatically switches from test mode to **live mode** on the next deploy.

That's it. After that, real customers pay with real cards and the money goes to your bank. 💰

---

## ❓ Common questions
- **Do I need a Stripe login?** Not for testing. You'll claim one when you go live.
- **Where do I see my sales?** In your Stripe Dashboard once you've claimed your account.
- **Can I refund someone?** Yes — from the Stripe Dashboard, or ask your builder to add a refund button.
- **Is it safe?** Yes. Card details go straight to Stripe — they never touch your website.

Need anything changed? Just ask your Emergent builder. 🙌
