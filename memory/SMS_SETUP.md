# Twilio SMS configuration

## Current status
Carrier email gateways are replaced by Twilio Programmable Messaging. Member sign-in/sign-up and admin phone verification accept the phone number alone. Google Voice/VoIP numbers are not blocked by line type or carrier. SMS success means Twilio accepted the message, not confirmed receipt.

No Twilio account credentials or sending number were found in the project or process configuration. **Real SMS delivery is blocked until these are supplied through backend environment configuration.** No runtime simulation, email-gateway fallback, or fabricated credentials are used.

## Required backend environment values
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- Exactly one of `TWILIO_PHONE_NUMBER` (SMS-capable, E.164) or `TWILIO_MESSAGING_SERVICE_SID` (with a configured sender pool).
- `DEFAULT_PHONE_REGION=US` is configured for unprefixed US/Canada numbers. International numbers must include `+` and country code.

Account details and sender configuration come from https://console.twilio.com/. These credentials cannot be derived from Resend, Gmail, Google sign-in, or the existing AI key. No Verify Service is required.

## Delivery restrictions
- Twilio trials restrict delivery to verified recipients.
- US long-code application traffic needs applicable A2P 10DLC approval; toll-free sending needs toll-free verification.
- Google Voice can receive ordinary SMS, but Google/Twilio/carrier filtering can prevent automated texts. Acceptance in the app is not a delivery guarantee.
- Existing email/Google member sign-in and admin TOTP/email/backup options remain available.

## Implementation
- `backend/sms_service.py`: official Twilio SDK; bounded network timeout, nonblocking send, safe error handling, E.164 validation without carrier lookups.
- `backend/sms_otp.py`: bcrypt-hashed codes, 10-minute expiry, atomic single-use verification and five-attempt limit, 30-second resend cooldown, 5 sends/number/hour and 100 total/hour limits in MongoDB. Failed sends cannot verify. Old email-gateway challenge records are not accepted.
- New SMS OTP records store UTC datetimes. TTL indexes remove expired challenge and rate-limit records.
- Verified legacy member numbers are found under their original ten-digit representation and normalized on next successful sign-in without losing account identity or favorites.
- Admin verification codes are bound to the pending number. Removing/replacing a verified number invalidates outstanding admin sign-in SMS codes; resetting 2FA revokes pending SMS challenges.

## Required live acceptance test (blocked)
With valid credentials and an approved sender: request one code to an opted-in Google Voice number, confirm receipt, verify once, and ensure replay fails. Repeat for an admin's enrolled phone and verify the other 2FA methods still work. Never claim real delivery from unit-test mocks or seeded OTPs.

## Verification completed 2026-09-25
- 27 targeted backend tests pass; positive SMS cases use TEST-ONLY mocked transport and isolated databases.
- Mobile member entry, admin challenge errors/fallbacks, and number-only forms were browser-tested. Admin setup error states also used TEST-ONLY mocked browser responses.
- Real SMS remains untested/blocked because no Twilio credentials/sender are configured.
- CORS uses explicit `CORS_ORIGINS` plus optional trusted `APP_URL`; the preview proxy's rewritten hostname is explicitly allowed, not a wildcard. Keep this environment list current if website origins change.