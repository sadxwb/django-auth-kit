from __future__ import annotations

import re

import strawberry
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from strawberry.types import Info

from django_auth_kit.jwt.service import JWTService
from django_auth_kit.models import UserEmail, UserMobile
from django_auth_kit.otp.service import OTPService
from django_auth_kit.ratelimit import check_rate_limit
from django_auth_kit.schema.enums import OtpPurpose
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
    async def send_otp(self, info: Info, input: SendOtpInput) -> OperationResult:
        """Send an OTP code to the given email or mobile."""
        allowed, retry_after = check_rate_limit(get_request(info), "send_otp")
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )

        purpose = input.purpose
        is_email = _is_email(input.identifier)

        # Contextual validation based on purpose
        if purpose == OtpPurpose.REGISTER:
            if is_email:
                if await UserEmail.objects.filter(
                    email=input.identifier, is_verified=True
                ).aexists():
                    return OperationResult(
                        success=False,
                        message="This email is already registered.",
                    )
            else:
                if await UserMobile.objects.filter(
                    mobile=input.identifier, is_verified=True
                ).aexists():
                    return OperationResult(
                        success=False,
                        message="This mobile is already registered.",
                    )
        elif purpose == OtpPurpose.FORGOT_PASSWORD:
            # Don't reveal whether the account exists
            if is_email:
                exists = await UserEmail.objects.filter(
                    email=input.identifier, is_primary=True
                ).aexists()
            else:
                exists = await UserMobile.objects.filter(
                    mobile=input.identifier, is_primary=True
                ).aexists()
            if not exists:
                return OperationResult(success=True, message="Code sent.")

        sent = await sync_to_async(OTPService.create_and_send)(
            identifier=input.identifier,
            purpose=purpose.value,
        )
        if not sent:
            return OperationResult(
                success=False,
                message="Please wait before requesting a new code.",
            )
        return OperationResult(success=True, message="Code sent.")

    @strawberry.mutation
    async def verify_otp(self, info: Info, input: VerifyOtpInput) -> OperationResult:
        """Verify an OTP code."""
        allowed, retry_after = check_rate_limit(get_request(info), "verify_otp")
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        success, message = OTPService.verify(
            identifier=input.identifier,
            code=input.code,
            purpose=input.purpose.value,
        )
        return OperationResult(success=success, message=message)

    @strawberry.mutation
    async def register(self, info: Info, input: RegisterInput) -> AuthResponse:
        """
        Register a new user with a verified OTP.

        Flow: send_otp -> verify_otp -> register
        """
        allowed, retry_after = check_rate_limit(get_request(info), "register")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        # Check OTP was verified for registration
        if not OTPService.is_verified(input.identifier, purpose="register"):
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
            if await UserEmail.objects.filter(
                email=input.identifier, is_verified=True
            ).aexists():
                return AuthResponse(
                    success=False, message="This email is already registered."
                )
        else:
            if await UserMobile.objects.filter(
                mobile=input.identifier, is_verified=True
            ).aexists():
                return AuthResponse(
                    success=False, message="This mobile is already registered."
                )

        # Determine username
        username = input.username or input.identifier

        if await User.objects.filter(username=username).aexists():
            return AuthResponse(
                success=False, message="This username is already taken."
            )

        # Create user
        create_kwargs = {
            "username": username,
            "password": input.password1,
            "first_name": input.first_name or "",
            "last_name": input.last_name or "",
        }
        if is_email:
            create_kwargs["email"] = input.identifier
        user = await sync_to_async(User.objects.create_user)(**create_kwargs)

        # Create the email/mobile record
        if is_email:
            await UserEmail.objects.acreate(
                user=user,
                email=input.identifier,
                is_verified=True,
                is_primary=True,
            )
        else:
            await UserMobile.objects.acreate(
                user=user,
                mobile=input.identifier,
                is_verified=True,
                is_primary=True,
            )

        OTPService.clear_verified(input.identifier, purpose="register")
        tokens = JWTService.create_token_pair(user)

        return AuthResponse(
            success=True,
            message="Registration successful.",
            tokens=AuthTokens(**tokens),
            user=await sync_to_async(_user_to_type)(user),
        )

    @strawberry.mutation
    async def login(self, info: Info, input: LoginInput) -> AuthResponse:
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
            record = await (
                UserEmail.objects.filter(email=input.identifier, is_primary=True)
                .select_related("user")
                .afirst()
            )
            if record:
                user = record.user
        else:
            record = await (
                UserMobile.objects.filter(mobile=input.identifier, is_primary=True)
                .select_related("user")
                .afirst()
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
            user=await sync_to_async(_user_to_type)(user),
        )

    @strawberry.mutation
    async def refresh_token(self, info: Info, input: RefreshTokenInput) -> AuthResponse:
        """Get a new token pair using a refresh token."""
        allowed, retry_after = check_rate_limit(get_request(info), "refresh_token")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )

        @sync_to_async
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
