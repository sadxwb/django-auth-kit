from __future__ import annotations

import strawberry
from strawberry.types import Info

from django_auth_kit.schema.inputs import UpdateProfileInput
from django_auth_kit.schema.queries import _user_to_type
from django_auth_kit.schema.types import AuthResponse


@strawberry.type
class ProfileMutation:
    @strawberry.mutation
    def update_profile(self, info: Info, input: UpdateProfileInput) -> AuthResponse:
        """Update the authenticated user's profile."""
        user = info.context.request.user
        if not user.is_authenticated:
            return AuthResponse(success=False, message="Authentication required.")

        update_fields = []
        if input.first_name is not None:
            user.first_name = input.first_name
            update_fields.append("first_name")
        if input.last_name is not None:
            user.last_name = input.last_name
            update_fields.append("last_name")

        if update_fields:
            user.save(update_fields=update_fields)

        return AuthResponse(
            success=True,
            message="Profile updated.",
            user=_user_to_type(user),
        )
