import re

import httpx

from app.core.config import get_settings

AFROMESSAGE_SEND_URL = "https://api.afromessage.com/api/send"
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")


class SMSNotConfigured(Exception):
    pass


class SMSProviderError(Exception):
    pass


def send_customer_sms(recipient: str, message: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.afromessage_api_key or not settings.afromessage_identifier_id:
        raise SMSNotConfigured
    if not _E164.fullmatch(recipient):
        raise ValueError("Customer phone must be in E.164 format")

    payload = {
        "from": settings.afromessage_identifier_id,
        "to": recipient,
        "message": message,
    }
    if settings.afromessage_sender:
        payload["sender"] = settings.afromessage_sender

    try:
        response = httpx.post(
            AFROMESSAGE_SEND_URL,
            headers={
                "Authorization": f"Bearer {settings.afromessage_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.sms_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SMSProviderError("AfroMessage request failed") from exc

    result = data.get("response") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or data.get("acknowledge") != "success"
        or not isinstance(result, dict)
        or not isinstance(result.get("message_id"), str)
        or not result["message_id"]
    ):
        raise SMSProviderError("AfroMessage did not accept the message")
    return {
        "message_id": result["message_id"],
        "status": str(result.get("status", "accepted")),
    }
