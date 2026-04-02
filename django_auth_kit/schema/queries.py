from __future__ import annotations

import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from django_auth_kit.schema.types import UserEmailType, UserMobileType, UserType
from django_auth_kit.schema.utils import get_authenticated_user


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


@strawberry.type(name="Query")
class UserProfileQuery:
    @strawberry.field
    async def me(self, info: Info) -> UserType:
        user = get_authenticated_user(info)
        return await sync_to_async(_user_to_type)(user)
