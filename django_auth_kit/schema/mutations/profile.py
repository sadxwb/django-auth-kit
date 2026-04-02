from __future__ import annotations

import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from django.db import models

from django_auth_kit.schema.queries import _user_to_type
from django_auth_kit.schema.types import AuthResponse, UpdateProfileInput, get_profile_fields
from django_auth_kit.schema.utils import get_current_user


def _apply_profile_updates(user, input):
    update_fields = []
    for field_name in get_profile_fields():
        value = getattr(input, field_name, None)
        if value is not None:
            field = user._meta.get_field(field_name)
            if isinstance(field, models.FileField):
                getattr(user, field_name).save(value.name, value, save=False)
            else:
                setattr(user, field_name, value)
            update_fields.append(field_name)
    if update_fields:
        user.save(update_fields=update_fields)


@strawberry.type(name="Mutation")
class ProfileMutation:
    @strawberry.mutation
    async def update_profile(
        self, info: Info, input: UpdateProfileInput
    ) -> AuthResponse:
        """Update the authenticated user's profile."""
        user = get_current_user(info)
        if not user.is_authenticated:
            return AuthResponse(success=False, message="Authentication required.")

        await sync_to_async(_apply_profile_updates)(user, input)

        return AuthResponse(
            success=True,
            message="Profile updated.",
            user=await sync_to_async(_user_to_type)(user),
        )
