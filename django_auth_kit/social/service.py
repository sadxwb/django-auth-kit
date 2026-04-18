from __future__ import annotations

from django.core.exceptions import ValidationError

from django_auth_kit import settings as kit_settings


def upsert_social_app(
    provider: str,
    client_id: str,
    client_secret: str,
    name: str | None = None,
):
    """
    Create or update the allauth SocialApp for a provider and link it to the
    current Site. Lets projects seed provider credentials from env vars
    without importing allauth directly.

    Returns (app, created).
    """
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site

    app, created = SocialApp.objects.update_or_create(
        provider=provider,
        defaults={
            "name": name or provider.capitalize(),
            "client_id": client_id,
            "secret": client_secret,
        },
    )
    app.sites.add(Site.objects.get_current())
    return app, created


class SocialLoginService:
    """
    Bridges GraphQL social login mutations to django-allauth's provider
    infrastructure.

    Instead of implementing provider-specific logic, this service delegates
    token verification and user creation entirely to allauth. Any provider
    that allauth supports (and that has ``supports_token_authentication = True``)
    works automatically.

    Flow:
        1. Resolve the allauth provider via ``get_provider()``.
        2. Call ``provider.verify_token()`` — allauth handles all
           provider-specific token validation and user-info extraction.
        3. Call ``sociallogin.lookup()`` — allauth matches against existing
           social accounts or emails.
        4. For new users, ``adapter.save_user()`` creates the user following
           allauth's adapter hooks and signals.
        5. Return the Django ``User`` instance so the caller can issue JWT
           tokens.
    """

    @classmethod
    def complete_login(cls, request, provider_id: str, token: dict):
        """
        Perform social login using allauth's provider infrastructure.

        Args:
            request: The Django HTTP request (or a request-like object).
            provider_id: The allauth provider id (e.g. "google", "apple").
            token: A dict with provider-specific token keys.
                   Typically ``{"id_token": "..."}`` or ``{"access_token": "..."}``.

        Returns:
            The authenticated Django User instance.

        Raises:
            ValueError: If the provider is not enabled, not configured, or
                        does not support token authentication.
            ValidationError: If allauth rejects the token.
        """
        from allauth.socialaccount.adapter import get_adapter

        # Check provider is enabled in AUTH_KIT settings
        enabled = kit_settings.SOCIAL_PROVIDERS()
        if enabled and provider_id not in enabled:
            raise ValueError(f"Provider '{provider_id}' is not enabled.")

        # Resolve the allauth provider (handles SocialApp lookup, sub-providers, etc.)
        adapter = get_adapter()
        client_id = token.get("client_id")
        try:
            provider = adapter.get_provider(request, provider_id, client_id=client_id)
        except Exception:
            raise ValueError(f"Provider '{provider_id}' is not configured.")

        # Provider must support token-based auth (as opposed to redirect-only OAuth)
        if not provider.supports_token_authentication:
            raise ValueError(
                f"Provider '{provider_id}' does not support token authentication. "
                "Use the OAuth redirect flow instead."
            )

        # Let allauth verify the token — this calls the provider's own
        # verify_token() which handles ID-token decoding (Apple, Google),
        # access-token exchange (Facebook), etc.
        sociallogin = provider.verify_token(request, token)

        # Let allauth look up existing accounts (by social account uid or
        # verified email matching).
        sociallogin.lookup()

        if sociallogin.is_existing:
            user = sociallogin.user
            if not user.is_active:
                raise ValueError("Account is disabled.")
        else:
            # New user — let allauth create and save them, respecting adapter
            # hooks (populate_user, save_user, is_open_for_signup, etc.).
            if not adapter.is_open_for_signup(request, sociallogin):
                raise ValueError("Sign up is currently closed.")
            adapter.save_user(request, sociallogin, form=None)
            user = sociallogin.user

        return user
