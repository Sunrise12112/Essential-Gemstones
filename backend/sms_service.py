"""Twilio SMS transport. No carrier lookup or VoIP restrictions."""
import asyncio
import logging
import os
import re

import phonenumbers
from fastapi import HTTPException
from requests.exceptions import RequestException
from twilio.base.exceptions import TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client


def normalize_phone(raw: str) -> str:
    value = (raw or "").strip()
    if not re.fullmatch(r"\+?[0-9 ().-]{7,40}", value):
        raise HTTPException(400, "Enter a valid phone number, including the country code outside the US or Canada.")
    region = os.environ.get("DEFAULT_PHONE_REGION")
    if not value.startswith("+") and not region:
        raise HTTPException(400, "Include your country code, starting with +.")
    try:
        number = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        raise HTTPException(400, "Enter a valid phone number.") from None
    # Validate the number, never its carrier or line type (Google Voice is allowed).
    if number.extension or not phonenumbers.is_valid_number(number):
        raise HTTPException(400, "Enter a valid phone number.")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def require_sms_config() -> tuple[str, str, dict]:
    sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    phone = (os.environ.get("TWILIO_PHONE_NUMBER") or "").strip()
    service = (os.environ.get("TWILIO_MESSAGING_SERVICE_SID") or "").strip()
    if not sid or not token or bool(phone) == bool(service):
        raise HTTPException(503, "Text verification is unavailable: SMS service is not configured. Please use another sign-in method.")
    sender = {"messaging_service_sid": service} if service else {"from_": phone}
    return sid, token, sender


async def send_sms(phone: str, text: str) -> str:
    sid, token, sender = require_sms_config()
    client = Client(sid, token, http_client=TwilioHttpClient(timeout=10))
    try:
        message = await asyncio.wait_for(
            asyncio.to_thread(client.messages.create, to=normalize_phone(phone), body=text, **sender),
            timeout=12,
        )
        if not message.sid or message.status in {"failed", "undelivered", "canceled"}:
            raise HTTPException(502, "The text could not be sent. Please use another sign-in method.")
        return message.sid
    except TwilioRestException as exc:
        # Never log the exception: it can contain account identifiers and phone numbers.
        logging.getLogger(__name__).warning("SMS provider rejected request (code %s)", exc.code)
        messages = {
            21211: "This phone number could not receive the text. Check the number and country code.",
            21614: "This number cannot receive SMS from the sender. Please use another sign-in method.",
            21608: "SMS is limited to verified recipients while the sending account is in trial mode. Please use another sign-in method.",
            21610: "Texts to this number are opted out. Please use another sign-in method.",
            30007: "The text was filtered by a provider. Please use another sign-in method.",
            20003: "Text verification is temporarily unavailable. Please use another sign-in method.",
            20429: "Too many text requests. Please wait before trying again.",
        }
        raise HTTPException(502, messages.get(exc.code, "The SMS provider could not send the text. Please try another sign-in method.")) from None
    except (asyncio.TimeoutError, RequestException):
        raise HTTPException(503, "The SMS provider did not respond. Please wait before requesting a new code.") from None
    except HTTPException:
        raise
    except Exception:
        logging.getLogger(__name__).warning("SMS transport unavailable")
        raise HTTPException(503, "Text verification is temporarily unavailable. Please use another sign-in method.") from None


def mask_phone(phone: str) -> str:
    return f"(•••) •••-{phone[-4:]}" if phone else ""