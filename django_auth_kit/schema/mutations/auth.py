from __future__ import annotations

import re

import strawberry
from django.contrib.auth import get_user_model
from strawberry.types import Info

from django_auth_kit.jwt.service import JWTService
from django_auth_kit.models import UserEmail, UserMobile
from django_auth_kit.otp.service import OTPService
from django_auth_kit.ratelimit import check_rate_limit
from django_auth_kit.schema.inputs import (
    LoginInput,
    RefreshTokenInput,
    RegisterInput,
    SendOtpInput,
    VerifyOtpInput,
)
from django_auth_kit.schema.utils import get_request
from django_auth_kit.schema.queries import _user_to_type
from django_auth_kit.schema.types import AuthResponse, AuthTokens, OperationResult

User = get_user_model()

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _is_email(identifier: str) -> bool:
    return bool(_EMAIL_RE.match(identifier))


@strawberry.type(name="Mutation")
class AuthMutation:
    @strawberry.mutation
    def send_otp(self, info: Info, input: SendOtpInput) -> OperationResult:
        """Send an OTP code to the given email or mobile."""
        allowed, retry_after = check_rate_limit(get_request(info), "send_otp")
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        sent = OTPService.create_and_send(
            identifier=input.identifier,
            purpose=input.purpose,
            channel=input.channel,
        )
        if not sent:
            return OperationResult(
                success=False,
                message="Please wait before requesting a new code.",
            )
        return OperationResult(success=True, message="Code sent.")

    @strawberry.mutation
    def verify_otp(self, info: Info, input: VerifyOtpInput) -> OperationResult:
        """Verify an OTP code."""
        allowed, retry_after = check_rate_limit(get_request(info), "verify_otp")
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        success, message = OTPService.verify(
            identifier=input.identifier,
            purpose=input.purpose,
            code=input.code,
        )
        return OperationResult(success=success, message=message)

    @strawberry.mutation
    def register(self, info: Info, input: RegisterInput) -> AuthResponse:
        """
        Register a new user with a verified OTP code.

        Flow: send_otp -> verify_otp -> register
        """
        allowed, retry_after = check_rate_limit(get_request(info), "register")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        # Check OTP was verified
        if not OTPService.is_verified(input.identifier, "register"):
            return AuthResponse(
                success=False, message="OTP not verified. Please verify first."
            )

        if input.password1 != input.password2:
            return AuthResponse(success=False, message="Passwords do not match.")

        if len(input.password1) < 8:
            return AuthResponse(
                success=False, message="Password must be at least 8 characters."
            )

        is_email = _is_email(input.identifier)

        # Check uniqueness
        if is_email:
            if UserEmail.objects.filter(
                email=input.identifier, is_verified=True
            ).exists():
                return AuthResponse(
                    success=False, message="This email is already registered."
                )
        else:
            if UserMobile.objects.filter(
                mobile=input.identifier, is_verified=True
            ).exists():
                return AuthResponse(
                    success=False, message="This mobile is already registered."
                )

        # Determine username
        username = input.username or input.identifier

        if User.objects.filter(username=username).exists():
            return AuthResponse(
                success=False, message="This username is already taken."
            )

        # Create user
        user = User.objects.create_user(
            username=username,
            password=input.password1,
            first_name=input.first_name or "",
            last_name=input.last_name or "",
        )

        # Create the email/mobile record
        if is_email:
            UserEmail.objects.create(
                user=user,
                email=input.identifier,
                is_verified=True,
                is_primary=True,
            )
            user.email = input.identifier
            user.save(update_fields=["email"])
        else:
            UserMobile.objects.create(
                user=user,
                mobile=input.identifier,
                is_verified=True,
                is_primary=True,
            )

        OTPService.clear_verified(input.identifier, "register")
        tokens = JWTService.create_token_pair(user)

        return AuthResponse(
            success=True,
            message="Registration successful.",
            tokens=AuthTokens(**tokens),
            user=_user_to_type(user),
        )

    @strawberry.mutation
    def login(self, info: Info, input: LoginInput) -> AuthResponse:
        """Login with email or mobile + password."""
        allowed, retry_after = check_rate_limit(get_request(info), "login")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        is_email = _is_email(input.identifier)

        user = None
        if is_email:
            record = (
                UserEmail.objects.filter(email=input.identifier, is_primary=True)
                .select_related("user")
                .first()
            )
            if record:
                user = record.user
        else:
            record = (
                UserMobile.objects.filter(mobile=input.identifier, is_primary=True)
                .select_related("user")
                .first()
            )
            if record:
                user = record.user

        if user is None or not user.check_password(input.password):
            return AuthResponse(success=False, message="Invalid credentials.")

        if not user.is_active:
            return AuthResponse(success=False, message="Account is disabled.")

        tokens = JWTService.create_token_pair(user)
        return AuthResponse(
            success=True,
            message="Login successful.",
            tokens=AuthTokens(**tokens),
            user=_user_to_type(user),
        )

    @strawberry.mutation
    def refresh_token(self, info: Info, input: RefreshTokenInput) -> AuthResponse:
        """Get a new token pair using a refresh token."""
        allowed, retry_after = check_rate_limit(get_request(info), "refresh_token")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )

        def _load_user(pk):
            return User.objects.filter(pk=pk, is_active=True).first()

        try:
            tokens = JWTService.refresh_access_token(
                input.refresh_token,
                user_loader=_load_user,
            )
        except Exception:
            return AuthResponse(
                success=False,
                message="Invalid or expired refresh token.",
            )

        return AuthResponse(
            success=True,
            message="Token refreshed.",
            tokens=AuthTokens(**tokens),
        )
