"""Password hashing and compact JWT primitives used by the identity module."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class TokenError(ValueError):
    """Raised when a JWT is malformed, expired or signed for another service."""


_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def hash_password(password: str) -> str:
    """Hash a password with a memory-hard, salted scrypt representation."""

    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return "$".join(
        (
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            _b64encode(salt),
            _b64encode(derived),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing parsing or comparison details."""

    try:
        algorithm, n, r, p, salt_text, digest_text = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (TypeError, ValueError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_access_token(
    *,
    subject: str,
    session_id: str,
    roles: list[str],
    secret: str,
    issuer: str,
    audience: str,
    expires_in: int,
) -> str:
    """Create an HS256 access token with an explicit session binding."""

    now = int(time.time())
    payload = {
        "sub": subject,
        "sid": session_id,
        "typ": "access",
        "roles": roles,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "jti": secrets.token_urlsafe(16),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def decode_access_token(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
) -> dict[str, Any]:
    """Verify an access token and return its claims."""

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
    except (
        ValueError,
        TypeError,
        UnicodeError,
        json.JSONDecodeError,
        base64.binascii.Error,
    ) as exc:
        raise TokenError("invalid token") from exc

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenError("invalid token payload")
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise TokenError("invalid token header")
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        received_signature = _b64decode(encoded_signature)
    except (TypeError, ValueError, base64.binascii.Error) as exc:
        raise TokenError("invalid token signature") from exc
    if not hmac.compare_digest(received_signature, expected_signature):
        raise TokenError("invalid token signature")

    now = int(time.time())
    if payload.get("typ") != "access":
        raise TokenError("invalid token type")
    if payload.get("iss") != issuer or payload.get("aud") != audience:
        raise TokenError("invalid token audience")
    if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("sid"), str):
        raise TokenError("invalid token subject")
    if not isinstance(payload.get("exp"), int) or payload["exp"] <= now:
        raise TokenError("expired token")
    return payload
