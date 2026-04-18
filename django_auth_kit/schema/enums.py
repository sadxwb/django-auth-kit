from __future__ import annotations

import enum

import strawberry


@strawberry.enum
class OtpPurpose(enum.Enum):
    REGISTER = "register"
    FORGOT_PASSWORD = "forgot_password"
    VERIFY_CONTACT = "verify_contact"
    CHANGE_PASSWORD = "change_password"
