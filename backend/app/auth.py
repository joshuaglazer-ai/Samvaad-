"""Demo-grade PIN auth for counsellor and admin endpoints (header X-Role-Pin).

This is NOT production auth: a shared PIN per role, compared in constant time. Replace with real
identity (e.g. SSO) before any live deployment. Documented in README "Known limitations".
"""
import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


def _check(pin: str | None, expected: str) -> None:
    if not pin or not hmac.compare_digest(pin.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing X-Role-Pin")


def require_counsellor(x_role_pin: str | None = Header(default=None)) -> str:
    s = get_settings()
    # Admins can also open the counsellor console.
    if x_role_pin and hmac.compare_digest(x_role_pin.encode(), s.admin_pin.encode()):
        return "admin"
    _check(x_role_pin, s.counsellor_pin)
    return "counsellor"


def require_admin(x_role_pin: str | None = Header(default=None)) -> str:
    _check(x_role_pin, get_settings().admin_pin)
    return "admin"
