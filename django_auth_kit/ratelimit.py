from __future__ import annotations

import hashlib
import time

from django.core.cache import cache

from django_auth_kit import settings as kit_settings

# DRF-style duration map
DURATION_MAP = {
    "s": 1,
    "sec": 1,
    "m": 60,
    "min": 60,
    "h": 3600,
    "hour": 3600,
    "d": 86400,
    "day": 86400,
}


def _parse_rate(rate: str) -> tuple[int, int]:
    """
    Parse a DRF-style rate string like "5/min" or "100/day".

    Returns:
        (num_requests, duration_seconds)
    """
    num, period = rate.split("/")
    num_requests = int(num)
    duration = DURATION_MAP.get(period)
    if duration is None:
        raise ValueError(
            f"Invalid rate period '{period}'. "
            f"Use one of: {', '.join(DURATION_MAP.keys())}"
        )
    return num_requests, duration


_UNKNOWN_IP = "__unknown__"


def _get_client_ip(request) -> str:
    """
    Extract client IP from the request, supporting reverse proxies.

    Returns a sentinel ``_UNKNOWN_IP`` when the IP cannot be determined.
    All unidentified clients share a single rate-limit bucket so that
    attackers cannot bypass limits by omitting IP headers.
    """
    # WSGI (standard Django)
    if hasattr(request, "META"):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        addr = request.META.get("REMOTE_ADDR")
        if addr:
            return addr
        return _UNKNOWN_IP

    # ASGI / Channels
    if hasattr(request, "headers"):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()

    if hasattr(request, "scope"):
        client = request.scope.get("client")
        if client:
            return client[0]

    return _UNKNOWN_IP


def _cache_key(action: str, ident: str) -> str:
    hashed = hashlib.md5(ident.encode()).hexdigest()  # noqa: S324
    return f"authkit:ratelimit:{action}:{hashed}"


def check_rate_limit(request, action: str) -> tuple[bool, int]:
    """
    Check if the request is within the rate limit for the given action.

    Args:
        request: Django HTTP request or ASGI scope
        action: The action name matching a key in RATE_LIMITS settings

    Returns:
        (allowed, retry_after_seconds)
        - allowed=True if request is within rate limit
        - retry_after_seconds > 0 when rate limited (seconds until next allowed request)
    """
    rates = kit_settings.RATE_LIMITS()
    rate_str = rates.get(action)
    if not rate_str:
        return True, 0

    num_requests, duration = _parse_rate(rate_str)
    ip = _get_client_ip(request)
    key = _cache_key(action, ip)

    now = time.time()
    history: list[float] = cache.get(key, [])

    # Remove entries outside the window
    cutoff = now - duration
    history = [t for t in history if t > cutoff]

    if len(history) >= num_requests:
        retry_after = int(history[0] - cutoff) + 1
        return False, retry_after

    history.append(now)
    cache.set(key, history, duration)
    return True, 0
