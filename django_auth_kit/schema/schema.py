import strawberry
from strawberry.tools import merge_types

from django_auth_kit.schema.mutations.auth import AuthMutation
from django_auth_kit.schema.mutations.password import PasswordMutation
from django_auth_kit.schema.mutations.profile import ProfileMutation
from django_auth_kit.schema.mutations.social import SocialMutation, SocialQuery
from django_auth_kit.schema.queries import UserProfileQuery

Mutation = merge_types(
    name="Mutation",
    types=(
        AuthMutation,
        PasswordMutation,
        ProfileMutation,
        SocialMutation,
    ),
)


Query = merge_types(
    name="Query",
    types=(
        UserProfileQuery,
        SocialQuery,
    ),
)


schema = strawberry.Schema(query=Query, mutation=Mutation)
