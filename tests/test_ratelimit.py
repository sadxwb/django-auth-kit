from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from django_auth_kit.ratelimit import (
    _UNKNOWN_IP,
    _cache_key,
    _get_client_ip,
    _parse_rate,
    check_rate_limit,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_request(ip: str = "127.0.0.1") -> MagicMock:
    request = MagicMock()
    request.META = {"REMOTE_ADDR": ip}
    return request


# ---------------------------------------------------------------------------
# _parse_rate
# ---------------------------------------------------------------------------


class TestParseRate:
    def test_per_second(self):
        assert _parse_rate("10/s") == (10, 1)

    def test_per_second_long(self):
        assert _parse_rate("10/sec") == (10, 1)

    def test_per_minute(self):
        assert _parse_rate("5/min") == (5, 60)

    def test_per_minute_short(self):
        assert _parse_rate("5/m") == (5, 60)

    def test_per_hour(self):
        assert _parse_rate("100/hour") == (100, 3600)

    def test_per_hour_short(self):
        assert _parse_rate("100/h") == (100, 3600)

    def test_per_day(self):
        assert _parse_rate("1000/day") == (1000, 86400)

    def test_per_day_short(self):
        assert _parse_rate("1000/d") == (1000, 86400)

    def test_invalid_period(self):
        with pytest.raises(ValueError, match="Invalid rate period"):
            _parse_rate("5/week")

    def test_large_number(self):
        assert _parse_rate("9999/min") == (9999, 60)

    def test_one_request(self):
        assert _parse_rate("1/s") == (1, 1)


# ---------------------------------------------------------------------------
# _get_client_ip
# ---------------------------------------------------------------------------


class TestGetClientIP:
    def test_remote_addr(self):
        request = _make_request("192.168.1.100")
        assert _get_client_ip(request) == "192.168.1.100"

    def test_xff_single(self):
        request = _make_request()
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.50"
        assert _get_client_ip(request) == "203.0.113.50"

    def test_xff_multiple_takes_first(self):
        request = _make_request()
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.50, 10.0.0.1, 172.16.0.1"
        assert _get_client_ip(request) == "203.0.113.50"

    def test_xff_strips_whitespace(self):
        request = _make_request()
        request.META["HTTP_X_FORWARDED_FOR"] = "  203.0.113.50  , 10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.50"

    def test_xff_takes_precedence_over_remote_addr(self):
        request = _make_request("127.0.0.1")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4"
        assert _get_client_ip(request) == "1.2.3.4"

    def test_missing_remote_addr_returns_unknown(self):
        request = MagicMock()
        request.META = {}
        assert _get_client_ip(request) == _UNKNOWN_IP

    def test_asgi_scope_client(self):
        """Channels / ASGI scope-based request."""
        request = MagicMock(spec=[])  # no META attribute
        request.headers = {}
        request.scope = {"client": ("10.0.0.5", 12345)}
        assert _get_client_ip(request) == "10.0.0.5"

    def test_asgi_xff_header(self):
        request = MagicMock(spec=[])
        request.headers = {"x-forwarded-for": "8.8.8.8, 10.0.0.1"}
        assert _get_client_ip(request) == "8.8.8.8"

    def test_completely_unknown_request_returns_unknown(self):
        request = MagicMock(spec=[])
        assert _get_client_ip(request) == _UNKNOWN_IP


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_deterministic(self):
        key1 = _cache_key("login", "127.0.0.1")
        key2 = _cache_key("login", "127.0.0.1")
        assert key1 == key2

    def test_different_actions(self):
        assert _cache_key("login", "127.0.0.1") != _cache_key("register", "127.0.0.1")

    def test_different_ips(self):
        assert _cache_key("login", "1.1.1.1") != _cache_key("login", "2.2.2.2")

    def test_prefix(self):
        key = _cache_key("login", "127.0.0.1")
        assert key.startswith("authkit:ratelimit:login:")


# ---------------------------------------------------------------------------
# check_rate_limit — core logic
# ---------------------------------------------------------------------------


class TestCheckRateLimit:
    def test_allows_within_limit(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "3/min"}}
        request = _make_request()

        for _ in range(3):
            allowed, _ = check_rate_limit(request, "login")
            assert allowed is True

    def test_blocks_over_limit(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "3/min"}}
        request = _make_request()

        for _ in range(3):
            check_rate_limit(request, "login")

        allowed, retry_after = check_rate_limit(request, "login")
        assert allowed is False
        assert retry_after > 0

    def test_retry_after_is_positive_integer(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "1/min"}}
        request = _make_request()

        check_rate_limit(request, "login")
        allowed, retry_after = check_rate_limit(request, "login")

        assert allowed is False
        assert isinstance(retry_after, int)
        assert 0 < retry_after <= 61

    def test_different_ips_have_separate_limits(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "2/min"}}

        req1 = _make_request("10.0.0.1")
        req2 = _make_request("10.0.0.2")

        for _ in range(2):
            check_rate_limit(req1, "login")

        allowed, _ = check_rate_limit(req1, "login")
        assert allowed is False

        allowed, _ = check_rate_limit(req2, "login")
        assert allowed is True

    def test_different_actions_have_separate_limits(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "2/min", "register": "2/min"}}
        request = _make_request()

        for _ in range(2):
            check_rate_limit(request, "login")

        allowed, _ = check_rate_limit(request, "login")
        assert allowed is False

        allowed, _ = check_rate_limit(request, "register")
        assert allowed is True

    def test_xff_header_used(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "1/min"}}

        request = _make_request()
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.50, 10.0.0.1"

        check_rate_limit(request, "login")
        allowed, _ = check_rate_limit(request, "login")
        assert allowed is False

        request2 = _make_request()
        request2.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.51"
        allowed, _ = check_rate_limit(request2, "login")
        assert allowed is True


# ---------------------------------------------------------------------------
# check_rate_limit — edge cases and configuration
# ---------------------------------------------------------------------------


class TestCheckRateLimitConfig:
    def test_no_rate_configured_allows_all(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {}}
        request = _make_request()

        for _ in range(100):
            allowed, _ = check_rate_limit(request, "login")
            assert allowed is True

    def test_action_not_in_rates_allows_all(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "1/min"}}
        request = _make_request()

        for _ in range(100):
            allowed, _ = check_rate_limit(request, "nonexistent_action")
            assert allowed is True

    def test_none_value_disables_action(self, settings):
        """Setting a rate to None should disable limiting for that action."""
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": None}}
        request = _make_request()

        for _ in range(100):
            allowed, _ = check_rate_limit(request, "login")
            assert allowed is True

    def test_unknown_ip_shares_bucket(self, settings):
        """When IP cannot be determined, requests share a single bucket."""
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "2/min"}}

        req1 = MagicMock(spec=[])  # no META, headers, or scope
        req2 = MagicMock(spec=[])

        check_rate_limit(req1, "login")
        check_rate_limit(req2, "login")

        # Third request from any unknown-IP client is blocked
        allowed, _ = check_rate_limit(req1, "login")
        assert allowed is False

    def test_uses_default_rates_when_no_override(self, settings):
        """When RATE_LIMITS is not in AUTH_KIT, defaults are used."""
        settings.AUTH_KIT = {}
        request = _make_request()

        # defaults have login at 5/min, so 5 should pass
        for _ in range(5):
            allowed, _ = check_rate_limit(request, "login")
            assert allowed is True

        allowed, _ = check_rate_limit(request, "login")
        assert allowed is False

    def test_per_second_rate(self, settings):
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "2/s"}}
        request = _make_request()

        for _ in range(2):
            allowed, _ = check_rate_limit(request, "login")
            assert allowed is True

        allowed, _ = check_rate_limit(request, "login")
        assert allowed is False

    def test_window_expires_and_allows_again(self, settings):
        """After the time window passes, requests should be allowed again."""
        settings.AUTH_KIT = {"RATE_LIMITS": {"login": "2/s"}}
        request = _make_request()

        # Exhaust the limit
        check_rate_limit(request, "login")
        check_rate_limit(request, "login")
        allowed, _ = check_rate_limit(request, "login")
        assert allowed is False

        # Simulate time passing by manipulating cache
        # The history entries will be outside the 1-second window
        key = _cache_key("login", "127.0.0.1")
        old_time = time.time() - 2  # 2 seconds ago
        cache.set(key, [old_time, old_time], 1)

        allowed, _ = check_rate_limit(request, "login")
        assert allowed is True


# ---------------------------------------------------------------------------
# check_rate_limit — all default actions
# ---------------------------------------------------------------------------


class TestDefaultActions:
    """Verify every default action key works with the default config."""

    @pytest.fixture(autouse=True)
    def _use_defaults(self, settings):
        settings.AUTH_KIT = {}

    @pytest.mark.parametrize(
        "action",
        [
            "send_otp",
            "verify_otp",
            "login",
            "register",
            "forgot_password",
            "social_login",
            "change_password",
            "refresh_token",
        ],
    )
    def test_default_action_is_rate_limited(self, action):
        request = _make_request()

        # All defaults allow at least 1 request
        allowed, _ = check_rate_limit(request, action)
        assert allowed is True

    @pytest.mark.parametrize(
        "action,expected_limit",
        [
            ("send_otp", 5),
            ("verify_otp", 5),
            ("login", 5),
            ("register", 3),
            ("forgot_password", 3),
            ("social_login", 5),
            ("change_password", 3),
            ("refresh_token", 10),
        ],
    )
    def test_default_action_blocks_at_limit(self, action, expected_limit):
        request = _make_request()

        for _ in range(expected_limit):
            allowed, _ = check_rate_limit(request, action)
            assert allowed is True

        allowed, _ = check_rate_limit(request, action)
        assert allowed is False
