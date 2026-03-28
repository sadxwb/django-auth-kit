from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from .base import BaseSmsBackend

if TYPE_CHECKING:
    from django_auth_kit.otp.service import SmsMessage


class ConsoleSmsBackend(BaseSmsBackend):
    """SMS backend that writes messages to stdout. Useful for development."""

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.stream = kwargs.get("stream", sys.stdout)

    def send_messages(self, messages: list[SmsMessage]) -> int:
        count = 0
        for message in messages:
            for recipient in message.to:
                self.stream.write(
                    f"--- SMS to {recipient} ---\n"
                    f"{message.body}\n"
                    f"--- End SMS ---\n\n"
                )
                count += 1
        self.stream.flush()
        return count
