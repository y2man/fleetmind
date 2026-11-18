import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

_N, _R, _P = 2**14, 8, 1


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_b64(salt)}${_b64(h)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        expected = base64.urlsafe_b64decode(h)
        got = hashlib.scrypt(password.encode(), salt=base64.urlsafe_b64decode(salt), n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


DUMMY_HASH = hash_password("not-a-real-password")  # keeps unknown-email logins as slow as real ones


def fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_token(sub: str, typ: str, expires: timedelta, **claims) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "type": typ, "iat": now, "exp": now + expires, "jti": uuid.uuid4().hex, **claims}
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def decode_token(token: str, typ: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise ValueError("invalid token") from e
    if payload.get("type") != typ:
        raise ValueError("wrong token type")
    return payload
