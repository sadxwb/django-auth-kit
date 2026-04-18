from __future__ import annotations

import logging

import strawberry
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired
from strawberry.types import Info

from django_auth_kit.invitation import decode_invitation_token
from django_auth_kit.jwt.service import JWTService
from django_auth_kit.models import UserEmail
from django_auth_kit.ratelimit import check_rate_limit
from django_auth_kit.schema.inputs import AcceptInvitationInput
from django_auth_kit.schema.queries import _user_to_type
from django_auth_kit.schema.types import AuthResponse, AuthTokens
from django_auth_kit.schema.utils import get_request

User = get_user_model()
logger = logging.getLogger(__name__)


@strawberry.type(name="Mutation")
class InvitationMutation:
    @strawberry.mutation
    async def accept_invitation(
        self, info: Info, input: AcceptInvitationInput
    ) -> AuthResponse:
        """
        Accept an invitation: validate the signed token, set the user's
        password, mark the matching ``UserEmail`` verified, and return a
        JWT token pair so the frontend can log the user straight in.
        """
        allowed, retry_after = check_rate_limit(get_request(info), "accept_invitation")
        if not allowed:
            return AuthResponse(
                success=False,
                message=f"Rate limit exceeded. Try again in {retry_after}s.",
            )

        if input.password1 != input.password2:
            return AuthResponse(success=False, message="Passwords do not match.")
        if len(input.password1) < 8:
            return AuthResponse(
                success=False, message="Password must be at least 8 characters."
            )

        try:
            payload = decode_invitation_token(input.token)
        except SignatureExpired:
            return AuthResponse(
                success=False, message="This invitation link has expired."
            )
        except BadSignature:
            return AuthResponse(
                success=False, message="Invalid invitation link."
            )

        user = await User.objects.filter(pk=payload.user_pk).afirst()
        if user is None:
            return AuthResponse(success=False, message="User no longer exists.")

        # Accepting the invitation is the activation event — set password,
        # activate the account, and verify the matching email in one go.
        await sync_to_async(user.set_password)(input.password1)
        user.is_active = True
        await sync_to_async(user.save)(update_fields=["password", "is_active"])

        await UserEmail.objects.filter(
            user=user, email=payload.email
        ).aupdate(is_verified=True)

        tokens = JWTService.create_token_pair(user)
        return AuthResponse(
            success=True,
            message="Invitation accepted.",
            tokens=AuthTokens(**tokens),
            user=await sync_to_async(_user_to_type)(user),
        )
