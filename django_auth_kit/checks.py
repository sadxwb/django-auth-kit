"""
Django system checks that validate the allauth-related settings required
when social login is enabled via ``AUTH_KIT["SOCIAL_PROVIDERS"]``.

Allauth enforces some of these itself at startup (e.g. its AccountMiddleware
must be in MIDDLEWARE), but the error messages don't mention django-auth-kit.
These checks surface the requirements earlier and point at AUTH_KIT settings.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register

from django_auth_kit import settings as kit_settings

_REQUIRED_APPS = [
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

_ACCOUNT_MIDDLEWARE = "allauth.account.middleware.AccountMiddleware"
_ALLAUTH_BACKEND = "allauth.account.auth_backends.AuthenticationBackend"
_KIT_BACKEND = "django_auth_kit.backends.AuthenticationBackend"


@register()
def check_social_settings(app_configs, **kwargs):
    """Validate social-login prerequisites when SOCIAL_PROVIDERS is configured."""
    providers = kit_settings.SOCIAL_PROVIDERS()
    if not providers:
        return []

    errors: list[Error] = []
    installed = set(getattr(settings, "INSTALLED_APPS", ()))
    middleware = list(getattr(settings, "MIDDLEWARE", ()))
    backends = list(getattr(settings, "AUTHENTICATION_BACKENDS", ()))

    for app in _REQUIRED_APPS:
        if app not in installed:
            errors.append(
                Error(
                    f"'{app}' must be in INSTALLED_APPS when "
                    "AUTH_KIT['SOCIAL_PROVIDERS'] is set.",
                    id="django_auth_kit.E001",
                )
            )

    for provider in providers:
        app = f"allauth.socialaccount.providers.{provider}"
        if app not in installed:
            errors.append(
                Error(
                    f"'{app}' must be in INSTALLED_APPS because "
                    f"AUTH_KIT['SOCIAL_PROVIDERS'] contains '{provider}'.",
                    id="django_auth_kit.E002",
                )
            )

    if not hasattr(settings, "SITE_ID"):
        errors.append(
            Error(
                "SITE_ID must be set when AUTH_KIT['SOCIAL_PROVIDERS'] is set.",
                id="django_auth_kit.E003",
            )
        )

    if _ACCOUNT_MIDDLEWARE not in middleware:
        errors.append(
            Error(
                f"'{_ACCOUNT_MIDDLEWARE}' must be in MIDDLEWARE when "
                "AUTH_KIT['SOCIAL_PROVIDERS'] is set.",
                id="django_auth_kit.E004",
            )
        )

    if _ALLAUTH_BACKEND not in backends and _KIT_BACKEND not in backends:
        errors.append(
            Error(
                f"Either '{_KIT_BACKEND}' or '{_ALLAUTH_BACKEND}' must be in "
                "AUTHENTICATION_BACKENDS when AUTH_KIT['SOCIAL_PROVIDERS'] is set.",
                id="django_auth_kit.E005",
            )
        )

    return errors
