"""
Authentication backend re-exports so consuming projects can reference them
via ``django_auth_kit.*`` string paths without importing ``allauth`` in their
settings.
"""

from __future__ import annotations

from allauth.account.auth_backends import (
    AuthenticationBackend as _AllauthAuthenticationBackend,
)


class AuthenticationBackend(_AllauthAuthenticationBackend):
    """
    Thin subclass of allauth's backend. Exists so projects list
    ``"django_auth_kit.backends.AuthenticationBackend"`` in
    ``AUTHENTICATION_BACKENDS`` instead of the underlying allauth path.
    """
