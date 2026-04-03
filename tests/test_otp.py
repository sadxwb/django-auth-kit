import pytest
from django.core.cache import cache

from django_auth_kit.otp.service import OTPService


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestOTPService:
    def test_generate_default_length(self):
        otp = OTPService.generate()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_custom_length(self):
        otp = OTPService.generate(length=8)
        assert len(otp) == 8

    def test_verify_correct_code(self):
        identifier = "test@example.com"
        purpose = "register"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier, purpose), "123456", 300)

        success, msg = OTPService.verify(identifier, "123456", purpose)
        assert success is True

    def test_verify_wrong_code(self):
        identifier = "test@example.com"
        purpose = "register"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier, purpose), "123456", 300)

        success, msg = OTPService.verify(identifier, "000000", purpose)
        assert success is False
        assert "Invalid" in msg

    def test_verify_expired(self):
        success, msg = OTPService.verify("none@example.com", "123456", "register")
        assert success is False
        assert "expired" in msg.lower() or "not found" in msg.lower()

    def test_is_verified_after_verify(self):
        identifier = "verified@example.com"
        purpose = "register"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier, purpose), "111111", 300)
        OTPService.verify(identifier, "111111", purpose)

        assert OTPService.is_verified(identifier, purpose) is True

    def test_clear_verified(self):
        identifier = "clear@example.com"
        purpose = "register"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier, purpose), "111111", 300)
        OTPService.verify(identifier, "111111", purpose)
        OTPService.clear_verified(identifier, purpose)

        assert OTPService.is_verified(identifier, purpose) is False

    def test_purpose_isolation(self):
        """OTP verified for one purpose must not be valid for another."""
        identifier = "user@example.com"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier, "register"), "111111", 300)
        OTPService.verify(identifier, "111111", "register")

        assert OTPService.is_verified(identifier, "register") is True
        assert OTPService.is_verified(identifier, "forgot_password") is False
