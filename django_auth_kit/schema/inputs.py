from __future__ import annotations

import strawberry


@strawberry.input
class SendOtpInput:
    identifier: str  # email or mobile
    purpose: str  # "register", "forgot_password"
    channel: str = "email"  # "email" or "sms"


@strawberry.input
class VerifyOtpInput:
    identifier: str
    purpose: str
    code: str


@strawberry.input
class RegisterInput:
    identifier: str  # email or mobile
    channel: str  # "email" or "sms"
    code: str  # verified OTP code
    password1: str
    password2: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@strawberry.input
class LoginInput:
    identifier: str  # email or mobile
    password: str


@strawberry.input
class RefreshTokenInput:
    refresh_token: str


@strawberry.input
class ChangePasswordInput:
    old_password: str
    new_password1: str
    new_password2: str


@strawberry.input
class ForgotPasswordInput:
    identifier: str  # email or mobile
    code: str  # verified OTP code
    new_password1: str
    new_password2: str


@strawberry.input
class UpdateProfileInput:
    first_name: str | None = None
    last_name: str | None = None


@strawberry.input
class SocialLoginInput:
    provider: str
    access_token: str | None = None
    id_token: str | None = None
    client_id: str | None = None
