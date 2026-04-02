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

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier), "123456", 300)

        success, msg = OTPService.verify(identifier, "123456")
        assert success is True

    def test_verify_wrong_code(self):
        identifier = "test@example.com"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier), "123456", 300)

        success, msg = OTPService.verify(identifier, "000000")
        assert success is False
        assert "Invalid" in msg

    def test_verify_expired(self):
        success, msg = OTPService.verify("none@example.com", "123456")
        assert success is False
        assert "expired" in msg.lower() or "not found" in msg.lower()

    def test_is_verified_after_verify(self):
        identifier = "verified@example.com"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier), "111111", 300)
        OTPService.verify(identifier, "111111")

        assert OTPService.is_verified(identifier) is True

    def test_clear_verified(self):
        identifier = "clear@example.com"

        from django_auth_kit.otp.service import _cache_key

        cache.set(_cache_key(identifier), "111111", 300)
        OTPService.verify(identifier, "111111")
        OTPService.clear_verified(identifier)

        assert OTPService.is_verified(identifier) is False
