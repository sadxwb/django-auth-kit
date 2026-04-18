from __future__ import annotations

import re

import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from django.db import models
from django.db.models.fields.files import FieldFile
from strawberry_django.fields.types import DjangoFileType, DjangoImageType

from django_auth_kit.models import UserEmail, UserMobile
from django_auth_kit.schema.types import (
    UserEmailType,
    UserMobileType,
    UserType,
    get_profile_fields,
)
from django_auth_kit.schema.utils import get_authenticated_user

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _file_to_type(field_file: FieldFile, field: models.Field) -> DjangoFileType | DjangoImageType | None:
    if not field_file:
        return None
    if isinstance(field, models.ImageField):
        return DjangoImageType(
            name=field_file.name,
            path=field_file.name,
            size=field_file.size,
            url=field_file.url,
            width=getattr(field_file, "width", 0),
            height=getattr(field_file, "height", 0),
        )
    return DjangoFileType(
        name=field_file.name,
        path=field_file.name,
        size=field_file.size,
        url=field_file.url,
    )


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

    kwargs: dict = {"id": strawberry.ID(str(user.pk)), "emails": emails, "mobiles": mobiles}
    for field_name in get_profile_fields():
        field = user._meta.get_field(field_name)
        if isinstance(field, models.FileField):
            kwargs[field_name] = _file_to_type(getattr(user, field_name), field)
        else:
            kwargs[field_name] = getattr(user, field_name)

    return UserType(**kwargs)


@strawberry.type(name="Query")
class UserProfileQuery:
    @strawberry.field
    async def me(self, info: Info) -> UserType:
        user = get_authenticated_user(info)
        return await sync_to_async(_user_to_type)(user)

    @strawberry.field
    async def identifier_exists(self, info: Info, identifier: str) -> bool:
        """
        Return True if an email or mobile is already registered.

        Used by the frontend to pre-check registration / add-user forms.
        Matches any ``UserEmail`` / ``UserMobile`` row (verified or not) so
        admin-created accounts and in-flight registrations both count.
        """
        identifier = identifier.strip()
        if not identifier:
            return False
        if _EMAIL_RE.match(identifier):
            return await UserEmail.objects.filter(email__iexact=identifier).aexists()
        return await UserMobile.objects.filter(mobile=identifier).aexists()
