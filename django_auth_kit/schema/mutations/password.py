from __future__ import annotations

import re

import strawberry
from strawberry.types import Info

from django_auth_kit.models import UserEmail, UserMobile
from django_auth_kit.otp.service import OTPService
from django_auth_kit.schema.inputs import ChangePasswordInput, ForgotPasswordInput
from django_auth_kit.schema.types import OperationResult

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _is_email(identifier: str) -> bool:
    return bool(_EMAIL_RE.match(identifier))


@strawberry.type
class PasswordMutation:
    @strawberry.mutation
    def change_password(
        self, info: Info, input: ChangePasswordInput
    ) -> OperationResult:
        """Change password for the authenticated user."""
        user = info.context.request.user
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
        user.save(update_fields=["password"])
        return OperationResult(success=True, message="Password changed successfully.")

    @strawberry.mutation
    def forgot_password(self, input: ForgotPasswordInput) -> OperationResult:
        """
        Reset password using a verified OTP.

        Flow: send_otp(purpose="forgot_password") -> verify_otp -> forgot_password
        """
        if not OTPService.is_verified(input.identifier, "forgot_password"):
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

        if user is None:
            # Silently ignore as per spec (don't reveal if account exists)
            OTPService.clear_verified(input.identifier, "forgot_password")
            return OperationResult(
                success=True,
                message="If the account exists, the password has been reset.",
            )

        user.set_password(input.new_password1)
        user.save(update_fields=["password"])
        OTPService.clear_verified(input.identifier, "forgot_password")

        return OperationResult(success=True, message="Password reset successfully.")
