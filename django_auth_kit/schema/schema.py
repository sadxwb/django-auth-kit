from __future__ import annotations

import strawberry

from django_auth_kit.schema.mutations.auth import AuthMutation
from django_auth_kit.schema.mutations.password import PasswordMutation
from django_auth_kit.schema.mutations.profile import ProfileMutation
from django_auth_kit.schema.mutations.social import SocialMutation
from django_auth_kit.schema.queries import Query


@strawberry.type
class Mutation(AuthMutation, PasswordMutation, ProfileMutation, SocialMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
