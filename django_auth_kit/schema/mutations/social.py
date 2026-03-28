from __future__ import annotations

import strawberry
from strawberry.types import Info

from django_auth_kit.schema.inputs import SocialLoginInput
from django_auth_kit.schema.types import AuthResponse


@strawberry.type
class SocialMutation:
    @strawberry.mutation
    def social_login(self, info: Info, input: SocialLoginInput) -> AuthResponse:
        """
        Authenticate via a social provider using an access token obtained client-side.

        Requires django-allauth to be installed and the provider to be enabled
        in AUTH_KIT["SOCIAL_PROVIDERS"].

        Supported providers: google, facebook, apple, microsoft, azure.
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
    from django.contrib.auth import get_user_model

    from django_auth_kit import settings as kit_settings
    from django_auth_kit.jwt.service import JWTService
    from django_auth_kit.models import UserEmail
    from django_auth_kit.schema.queries import _user_to_type
    from django_auth_kit.schema.types import AuthTokens

    enabled_providers = kit_settings.SOCIAL_PROVIDERS()
    if input.provider not in enabled_providers:
        return AuthResponse(
            success=False,
            message=f"Provider '{input.provider}' is not enabled.",
        )

    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
    from allauth.socialaccount.providers import registry

    request = info.context.request
    User = get_user_model()

    provider_cls = registry.by_id(input.provider, request)
    if provider_cls is None:
        return AuthResponse(
            success=False,
            message=f"Provider '{input.provider}' is not configured.",
        )

    # Use the provider's API to fetch user info with the access token
    social_app = SocialApp.objects.filter(provider=input.provider).first()
    if social_app is None:
        return AuthResponse(
            success=False,
            message=f"No SocialApp configured for '{input.provider}'.",
        )

    # Complete the social login flow
    from allauth.socialaccount.helpers import complete_social_login
    from allauth.socialaccount.models import SocialLogin

    # Fetch user info from provider using the access token
    provider = provider_cls
    token = SocialToken(app=social_app, token=input.access_token)

    # Build a SocialLogin from token
    login = provider.sociallogin_from_response(request, _fetch_provider_user(input.provider, input.access_token))

    # Check if social account already exists
    existing = SocialAccount.objects.filter(
        provider=input.provider, uid=login.account.uid
    ).select_related("user").first()

    if existing:
        user = existing.user
        if not user.is_active:
            return AuthResponse(success=False, message="Account is disabled.")
    else:
        # Create new user from social data
        extra_data = login.account.extra_data
        email = extra_data.get("email", "")
        first_name = extra_data.get("given_name", extra_data.get("first_name", ""))
        last_name = extra_data.get("family_name", extra_data.get("last_name", ""))
        username = email.split("@")[0] if email else f"{input.provider}_{login.account.uid}"

        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_unusable_password()
        user.save()

        # Create social account
        SocialAccount.objects.create(
            user=user,
            provider=input.provider,
            uid=login.account.uid,
            extra_data=login.account.extra_data,
        )

        # Create email record if available
        if email:
            UserEmail.objects.get_or_create(
                user=user,
                email=email,
                defaults={"is_verified": True, "is_primary": True},
            )

    # Save / update token
    SocialToken.objects.update_or_create(
        app=social_app,
        account=SocialAccount.objects.get(user=user, provider=input.provider),
        defaults={"token": input.access_token},
    )

    tokens = JWTService.create_token_pair(user)
    return AuthResponse(
        success=True,
        message="Social login successful.",
        tokens=AuthTokens(**tokens),
        user=_user_to_type(user),
    )


def _fetch_provider_user(provider: str, access_token: str) -> dict:
    """Fetch user info from the social provider's API."""
    import requests

    urls = {
        "google": "https://www.googleapis.com/oauth2/v3/userinfo",
        "facebook": "https://graph.facebook.com/me?fields=id,name,email,first_name,last_name,picture",
        "microsoft": "https://graph.microsoft.com/v1.0/me",
        "azure": "https://graph.microsoft.com/v1.0/me",
    }

    url = urls.get(provider)
    if url is None:
        raise ValueError(f"Unsupported provider for user info fetch: {provider}")

    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Normalize to common fields
    if provider == "google":
        return {
            "id": data.get("sub"),
            "email": data.get("email", ""),
            "given_name": data.get("given_name", ""),
            "family_name": data.get("family_name", ""),
            "picture": data.get("picture", ""),
        }
    elif provider == "facebook":
        return {
            "id": data.get("id"),
            "email": data.get("email", ""),
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "picture": data.get("picture", {}).get("data", {}).get("url", ""),
        }
    elif provider in ("microsoft", "azure"):
        return {
            "id": data.get("id"),
            "email": data.get("mail", data.get("userPrincipalName", "")),
            "given_name": data.get("givenName", ""),
            "family_name": data.get("surname", ""),
        }

    return data
