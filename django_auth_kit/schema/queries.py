from __future__ import annotations

import strawberry
from strawberry.types import Info

from django_auth_kit.schema.types import UserEmailType, UserMobileType, UserType


def _get_authenticated_user(info: Info):
    user = info.context.request.user
    if not user.is_authenticated:
        raise PermissionError("Authentication required.")
    return user


def _user_to_type(user) -> UserType:
    emails = [
        UserEmailType(
            id=strawberry.ID(str(e.pk)),
            email=e.email,
            is_verified=e.is_verified,
            is_primary=e.is_primary,
        )
        for e in user.emails.all()
    ]
    mobiles = [
        UserMobileType(
            id=strawberry.ID(str(m.pk)),
            mobile=m.mobile,
            is_verified=m.is_verified,
            is_primary=m.is_primary,
        )
        for m in user.mobiles.all()
    ]

    return UserType(
        id=strawberry.ID(str(user.pk)),
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        emails=emails,
        mobiles=mobiles,
    )


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> UserType:
        user = _get_authenticated_user(info)
        return _user_to_type(user)
