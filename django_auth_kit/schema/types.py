from __future__ import annotations

import dataclasses
from typing import Optional

import strawberry

from django.contrib.auth import get_user_model
from django.db import models
from strawberry_django.fields.types import field_type_map, input_field_type_map

from django_auth_kit.settings import get_setting


@strawberry.type
class AuthTokens:
    access_token: str
    refresh_token: str


@strawberry.type
class OperationResult:
    success: bool
    message: str


@strawberry.type
class UserEmailType:
    id: strawberry.ID
    email: str
    is_verified: bool
    is_primary: bool


@strawberry.type
class UserMobileType:
    id: strawberry.ID
    mobile: str
    is_verified: bool
    is_primary: bool


# --- Dynamic UserType construction based on settings ---

def _get_field_type(field: models.Field, *, is_input: bool = False) -> type:
    """Derive the Python type from a Django model field, respecting nullability."""
    if is_input and type(field) in input_field_type_map:
        py_type = input_field_type_map[type(field)]
    else:
        py_type = field_type_map.get(type(field), str)
    if getattr(field, "null", False):
        return Optional[py_type]
    return py_type


def get_extra_profile_fields() -> list[str]:
    """Return the list of extra user model fields beyond the defaults."""
    extra = get_setting("EXTRA_USER_PROFILE_FIELDS", [])
    fields = list(extra)

    if not fields:
        return fields

    User = get_user_model()
    invalid = [f for f in fields if not hasattr(User, f)]
    if invalid:
        raise ValueError(
            f"AUTH_KIT: invalid user profile field(s): {invalid}. "
            f"'{User.__name__}' has no such attribute(s)."
        )
    return fields


def get_profile_fields() -> list[str]:
    """Return all profile fields (defaults + extras)."""
    return ["first_name", "last_name"] + get_extra_profile_fields()


def _build_user_type():
    extra_fields = get_extra_profile_fields()

    if not extra_fields:
        return _DefaultUserType

    User = get_user_model()
    type_fields: list[tuple] = []
    for name in extra_fields:
        field = User._meta.get_field(name)
        type_fields.append((name, _get_field_type(field)))

    dc = dataclasses.make_dataclass("UserType", type_fields, bases=(_DefaultUserType,))
    return strawberry.type(dc)


def _build_update_profile_input():
    extra_fields = get_extra_profile_fields()

    if not extra_fields:
        return _DefaultUpdateProfileInput

    User = get_user_model()
    input_fields: list[tuple] = []
    for name in extra_fields:
        field = User._meta.get_field(name)
        py_type = _get_field_type(field, is_input=True)
        input_fields.append(
            (name, Optional[py_type], dataclasses.field(default=None))
        )

    dc = dataclasses.make_dataclass(
        "UpdateProfileInput", input_fields, bases=(_DefaultUpdateProfileInput,)
    )
    return strawberry.input(dc)


@strawberry.type
class _DefaultUserType:
    id: strawberry.ID
    first_name: str
    last_name: str
    emails: list[UserEmailType]
    mobiles: list[UserMobileType]


@strawberry.input
class _DefaultUpdateProfileInput:
    first_name: Optional[str] = None
    last_name: Optional[str] = None


UserType = _build_user_type()
UpdateProfileInput = _build_update_profile_input()


@strawberry.type
class AuthResponse:
    success: bool
    message: str
    tokens: AuthTokens | None = None
    user: UserType | None = None