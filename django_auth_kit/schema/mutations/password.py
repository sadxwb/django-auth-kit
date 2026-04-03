from __future__ import annotations

import re

import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from django_auth_kit.models import UserEmail, UserMobile
from django_auth_kit.otp.service import OTPService
from django_auth_kit.ratelimit import check_rate_limit
from django_auth_kit.schema.inputs import ChangePasswordInput, ForgotPasswordInput
from django_auth_kit.schema.utils import get_request
from django_auth_kit.schema.types import OperationResult
from django_auth_kit.schema.utils import get_current_user

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _is_email(identifier: str) -> bool:
    return bool(_EMAIL_RE.match(identifier))


@strawberry.type(name="Mutation")
class PasswordMutation:
    @strawberry.mutation
    async def change_password(
        self, info: Info, input: ChangePasswordInput
    ) -> OperationResult:
        """Change password for the authenticated user."""
        allowed, retry_after = check_rate_limit(
            get_request(info), "change_password"
        )
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        user = get_current_user(info)
        if not user.is_authenticated:
            return OperationResult(success=False, message="Authentication required.")

        if not user.check_password(input.old_password):
            return OperationResult(
                success=False, message="Current password is incorrect."
            )

        if input.new_password1 != input.new_password2:
            return OperationResult(success=False, message="New passwords do not match.")

        if len(input.new_password1) < 8:
            return OperationResult(
                success=False, message="Password must be at least 8 characters."
            )

        user.set_password(input.new_password1)
        await user.asave(update_fields=["password"])
        return OperationResult(success=True, message="Password changed successfully.")

    @strawberry.mutation
    async def forgot_password(
        self, info: Info, input: ForgotPasswordInput
    ) -> OperationResult:
        """
        Reset password using a verified OTP.

        Flow: send_otp -> verify_otp -> forgot_password
        """
        allowed, retry_after = check_rate_limit(
            get_request(info), "forgot_password"
        )
        if not allowed:
            return OperationResult(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )
        if not OTPService.is_verified(input.identifier, purpose="forgot_password"):
            return OperationResult(
                success=False, message="OTP not verified. Please verify first."
            )

        if input.new_password1 != input.new_password2:
            return OperationResult(success=False, message="Passwords do not match.")

        if len(input.new_password1) < 8:
            return OperationResult(
                success=False, message="Password must be at least 8 characters."
            )

        # Find user by identifier
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

        if user is None:
            OTPService.clear_verified(input.identifier, purpose="forgot_password")
            return OperationResult(
                success=True,
                message="If the account exists, the password has been reset.",
            )

        user.set_password(input.new_password1)
        await user.asave(update_fields=["password"])
        OTPService.clear_verified(input.identifier, purpose="forgot_password")

        return OperationResult(success=True, message="Password reset successfully.")
