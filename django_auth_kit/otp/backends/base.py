from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django_auth_kit.otp.service import SmsMessage


class BaseSmsBackend:
    """Base class for SMS backends. Follows the Django email backend pattern."""

    def __init__(self, fail_silently: bool = False, **kwargs):
        self.fail_silently = fail_silently

    def open(self) -> bool | None:
        """Open a connection. Return True if a new connection was created."""
        return None

    def close(self) -> None:
        """Close the connection."""
        pass

    def send_messages(self, messages: list[SmsMessage]) -> int:
        """
        Send one or more SmsMessage objects and return the number sent.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses of BaseSmsBackend must implement send_messages()."
        )

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
