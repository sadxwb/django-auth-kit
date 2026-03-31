from __future__ import annotations

import strawberry
from strawberry.types import Info

from django_auth_kit.schema.inputs import SocialLoginInput
from django_auth_kit.schema.types import AuthResponse


@strawberry.type(name="Mutation")
class SocialMutation:
    @strawberry.mutation
    def social_login(self, info: Info, input: SocialLoginInput) -> AuthResponse:
        """
        Authenticate via a social provider using a token obtained client-side.

        Requires django-allauth to be installed with the desired provider
        configured. The provider must also be listed in
        AUTH_KIT["SOCIAL_PROVIDERS"].

        Pass ``access_token`` or ``id_token`` depending on the provider:
        - Google, Apple, OpenID Connect: ``id_token``
        - Facebook: ``access_token``

        All user creation, account linking, and email matching is handled
        by django-allauth's adapter infrastructure.
        """
        try:
            return _do_social_login(info, input)
        except ImportError:
            return AuthResponse(
                success=False,
                message="Social login is not available. Install django-allauth.",
            )
        except Exception as e:
            return AuthResponse(success=False, message=str(e))


def _do_social_login(info: Info, input: SocialLoginInput) -> AuthResponse:
    from django_auth_kit.jwt.service import JWTService
    from django_auth_kit.schema.queries import _user_to_type
    from django_auth_kit.schema.types import AuthTokens
    from django_auth_kit.social.service import SocialLoginService

    request = info.context.request

    # Build the token dict that allauth providers expect
    token = {}
    if input.access_token:
        token["access_token"] = input.access_token
    if input.id_token:
        token["id_token"] = input.id_token
    if input.client_id:
        token["client_id"] = input.client_id

    if not token.get("access_token") and not token.get("id_token"):
        return AuthResponse(
            success=False,
            message="Either access_token or id_token is required.",
        )

    user = SocialLoginService.complete_login(request, input.provider, token)

    tokens = JWTService.create_token_pair(user)
    return AuthResponse(
        success=True,
        message="Social login successful.",
        tokens=AuthTokens(**tokens),
        user=_user_to_type(user),
    )
