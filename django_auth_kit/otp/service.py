from __future__ import annotations

import secrets
from dataclasses import dataclass
from importlib import import_module

from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string

import re

from django_auth_kit import settings as kit_settings
from django_auth_kit.otp.backends.base import BaseSmsBackend

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


@dataclass
class SmsMessage:
    body: str
    to: list[str]


def _get_sms_backend() -> BaseSmsBackend:
    backend_path = kit_settings.SMS_BACKEND()
    module_path, class_name = backend_path.rsplit(".", 1)
    module = import_module(module_path)
    backend_cls = getattr(module, class_name)
    return backend_cls()


def _cache_key(identifier: str, purpose: str) -> str:
    return f"authkit:otp:{purpose}:{identifier}"


def _attempts_key(identifier: str, purpose: str) -> str:
    return f"authkit:otp_attempts:{purpose}:{identifier}"


def _cooldown_key(identifier: str, purpose: str) -> str:
    return f"authkit:otp_cooldown:{purpose}:{identifier}"


def _verified_key(identifier: str, purpose: str) -> str:
    return f"authkit:otp_verified:{purpose}:{identifier}"


class OTPService:
    """Handles OTP generation, storage (cache-based), verification, and delivery."""

    @staticmethod
    def generate(length: int | None = None) -> str:
        length = length or kit_settings.OTP_LENGTH()
        return "".join(str(secrets.randbelow(10)) for _ in range(length))

    @classmethod
    def create_and_send(cls, identifier: str, purpose: str) -> bool:
        """
        Generate an OTP, store it, and send via email or SMS.

        Channel is auto-detected from the identifier format.

        Args:
            identifier: email address or mobile number
            purpose: the action this OTP is for (e.g. "register", "forgot_password")

        Returns:
            True if sent successfully.
        """
        cooldown_k = _cooldown_key(identifier, purpose)
        if cache.get(cooldown_k):
            return False  # cooldown still active

        otp = cls.generate()
        timeout = kit_settings.OTP_TIMEOUT()

        cache.set(_cache_key(identifier, purpose), otp, timeout)
        cache.delete(_attempts_key(identifier, purpose))
        cache.set(cooldown_k, True, kit_settings.OTP_COOLDOWN())

        if _EMAIL_RE.match(identifier):
            cls._send_email(identifier, otp)
        else:
            cls._send_sms(identifier, otp)

        return True

    @classmethod
    def verify(cls, identifier: str, code: str, purpose: str) -> tuple[bool, str]:
        """
        Verify an OTP code.

        Returns:
            (success, message)
        """
        attempts_k = _attempts_key(identifier, purpose)
        max_attempts = kit_settings.OTP_MAX_ATTEMPTS()
        attempts = cache.get(attempts_k, 0)

        if attempts >= max_attempts:
            return False, "Too many attempts. Please request a new code."

        stored = cache.get(_cache_key(identifier, purpose))
        if stored is None:
            return False, "Code expired or not found. Please request a new one."

        if not secrets.compare_digest(stored, code):
            cache.set(attempts_k, attempts + 1, kit_settings.OTP_TIMEOUT())
            return False, "Invalid code."

        # Mark as verified
        cache.set(_verified_key(identifier, purpose), True, kit_settings.OTP_TIMEOUT())
        cache.delete(_cache_key(identifier, purpose))
        cache.delete(attempts_k)
        return True, "Code verified."

    @classmethod
    def is_verified(cls, identifier: str, purpose: str) -> bool:
        """Check if identifier has been verified via OTP."""
        return bool(cache.get(_verified_key(identifier, purpose)))

    @classmethod
    def clear_verified(cls, identifier: str, purpose: str) -> None:
        cache.delete(_verified_key(identifier, purpose))

    # --- Delivery methods ---

    @staticmethod
    def _send_email(email: str, otp: str) -> None:
        context = {"otp": otp, "email": email}
        text_body = render_to_string("django_auth_kit/otp_email.txt", context)
        html_body = render_to_string("django_auth_kit/otp_email.html", context)

        send_mail(
            subject=kit_settings.OTP_EMAIL_SUBJECT(),
            message=text_body,
            from_email=kit_settings.OTP_EMAIL_FROM(),
            recipient_list=[email],
            html_message=html_body,
        )

    @staticmethod
    def _send_sms(mobile: str, otp: str) -> None:
        body = f"Your verification code is: {otp}"
        message = SmsMessage(body=body, to=[mobile])
        backend = _get_sms_backend()
        backend.send_messages([message])
