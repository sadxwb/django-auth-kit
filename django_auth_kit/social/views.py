"""
OAuth2 redirect-based login views (async).

These views handle the standard OAuth2 authorization-code flow for providers
that do not support token-based authentication (e.g. Microsoft / Azure AD,
GitHub). The flow is:

    1. GET /social/<provider>/login/   → redirect to provider's auth page
    2. Provider redirects back to:
       GET /social/<provider>/callback/ → exchange code → issue JWT → redirect
"""

from __future__ import annotations

import secrets
from importlib import import_module
from urllib.parse import urlencode

import httpx
from asgiref.sync import sync_to_async
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views import View

from django_auth_kit import settings as kit_settings
from django_auth_kit.jwt.service import JWTService


def _get_oauth2_adapter_class(provider_id: str):
    """
    Dynamically discover the ``OAuth2Adapter`` subclass for an allauth provider.

    Each allauth OAuth2 provider ships a ``views`` module containing an adapter
    class that declares ``authorize_url``, ``access_token_url``, ``profile_url``,
    and a ``complete_login()`` method.
    """
    from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter

    module_path = f"allauth.socialaccount.providers.{provider_id}.views"
    try:
        module = import_module(module_path)
    except ImportError as exc:
        raise ValueError(
            f"No allauth provider module for '{provider_id}'. "
            f"Install 'allauth.socialaccount.providers.{provider_id}'."
        ) from exc

    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, OAuth2Adapter)
            and obj is not OAuth2Adapter
        ):
            return obj

    raise ValueError(
        f"No OAuth2Adapter subclass found in {module_path}. "
        f"Provider '{provider_id}' may not be an OAuth2 provider."
    )


def _error_redirect(redirect_url: str | None, error: str):
    """Redirect to frontend with error, or return 400 if no redirect URL."""
    if redirect_url:
        separator = "&" if "?" in redirect_url else "?"
        params = urlencode({"error": error})
        return HttpResponseRedirect(f"{redirect_url}{separator}{params}")
    return HttpResponseBadRequest(error)


def _store_oauth_state(session, state: str, provider_id: str, next_url: str | None):
    """Persist OAuth CSRF state + next-url into the session in one sync call.

    Invoked via sync_to_async from the async views — each session mutation
    triggers a DB read (session load) which Django forbids from an async
    context without wrapping.
    """
    session["authkit_oauth2_state"] = state
    session["authkit_oauth2_provider"] = provider_id
    if next_url:
        session["authkit_oauth2_next"] = next_url


def _pop_oauth_state(session) -> tuple[str | None, str | None, str | None]:
    """Pop the three OAuth session entries written by _store_oauth_state."""
    return (
        session.pop("authkit_oauth2_state", None),
        session.pop("authkit_oauth2_provider", None),
        session.pop("authkit_oauth2_next", None),
    )


def _build_authorize_redirect(request, AdapterClass, provider, app, callback_url, state):
    """
    Compose the provider authorize URL with query string.

    Several allauth primitives we touch here (``provider.get_scope_from_request``,
    ``provider.get_settings``, and the adapter's ``authorize_url`` — which,
    for Microsoft, resolves the tenant by querying the SocialApp) issue DB
    queries. This helper exists so the async login view can run the whole
    chain via ``sync_to_async``.
    """
    oauth2_adapter = AdapterClass(request)
    # ``get_scope_from_request(request)`` is the request-aware public API in
    # current allauth; ``get_scope()`` takes no args. Don't fall back to an
    # empty list on failure — Microsoft (and any OAuth2 server) will reject
    # an authorize request without ``scope``.
    scope = provider.get_scope_from_request(request)

    params = {
        "client_id": app.client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "state": state,
    }
    if scope:
        params["scope"] = " ".join(scope)
    provider_settings = provider.get_settings()
    params.update(provider_settings.get("AUTH_PARAMS", {}))

    return f"{oauth2_adapter.authorize_url}?{urlencode(params)}"


class OAuthLoginView(View):
    """
    Initiate the OAuth2 authorization-code flow.

    ``GET /social/<provider>/login/?next=<frontend_url>``

    Builds the provider's authorization URL, stores a CSRF ``state`` token
    in the session, and redirects the user to the provider's login page.

    Query params:
        next  – URL to redirect to after login (overrides
                ``AUTH_KIT["SOCIAL_LOGIN_REDIRECT_URL"]``).
    """

    async def get(self, request, provider_id):
        from allauth.socialaccount.adapter import get_adapter

        # Check provider is enabled
        enabled = kit_settings.SOCIAL_PROVIDERS()
        if enabled and provider_id not in enabled:
            return HttpResponseBadRequest(f"Provider '{provider_id}' is not enabled.")

        # Resolve allauth provider. ``adapter.get_provider`` already resolves
        # the associated SocialApp (respecting the current Site) and attaches
        # it to ``provider.app``, so we don't need a second lookup.
        adapter = get_adapter()
        try:
            provider = await sync_to_async(adapter.get_provider)(request, provider_id)
        except Exception:
            return HttpResponseBadRequest(
                f"Provider '{provider_id}' is not configured."
            )

        app = getattr(provider, "app", None)
        if not app:
            return HttpResponseBadRequest(
                f"No SocialApp configured for '{provider_id}'."
            )

        # Generate CSRF state
        state = secrets.token_urlsafe(32)
        next_url = request.GET.get("next", kit_settings.SOCIAL_LOGIN_REDIRECT_URL())
        await sync_to_async(_store_oauth_state)(
            request.session, state, provider_id, next_url
        )

        # Build server callback URL
        callback_path = reverse("django_auth_kit:oauth_callback", args=[provider_id])
        callback_url = request.build_absolute_uri(callback_path)

        AdapterClass = _get_oauth2_adapter_class(provider_id)

        # Reading ``provider.get_scope``/``get_settings`` and the adapter's
        # ``authorize_url`` can each trigger a DB query (e.g. Microsoft's
        # adapter looks up the SocialApp to derive the tenant URL). Build the
        # full redirect URL inside a sync helper so the whole chain runs in a
        # thread.
        authorize_redirect = await sync_to_async(_build_authorize_redirect)(
            request, AdapterClass, provider, app, callback_url, state
        )
        return HttpResponseRedirect(authorize_redirect)


class OAuthCallbackView(View):
    """
    Handle the OAuth2 callback from the provider.

    ``GET /social/<provider>/callback/?code=...&state=...``

    Validates the CSRF state, exchanges the authorization code for an
    access token, uses allauth's adapter to complete the login (fetch
    user profile, create/link accounts), issues JWT tokens, and redirects
    to the frontend.
    """

    async def get(self, request, provider_id):
        from allauth.socialaccount.adapter import get_adapter
        from allauth.socialaccount.models import SocialToken

        # Pop session state (session load hits the DB, so must go through
        # sync_to_async from this async view).
        expected_state, expected_provider, next_url = await sync_to_async(
            _pop_oauth_state
        )(request.session)

        # Validate state (CSRF protection)
        state = request.GET.get("state")
        if not state or state != expected_state:
            return _error_redirect(next_url, "Invalid or expired OAuth state.")

        if provider_id != expected_provider:
            return _error_redirect(next_url, "Provider mismatch.")

        # Check for errors from provider (e.g. user denied consent)
        error = request.GET.get("error")
        if error:
            error_desc = request.GET.get("error_description", error)
            return _error_redirect(next_url, error_desc)

        code = request.GET.get("code")
        if not code:
            return _error_redirect(next_url, "No authorization code received.")

        # Resolve provider (and its SocialApp via ``provider.app``).
        allauth_adapter = get_adapter()
        try:
            provider = await sync_to_async(allauth_adapter.get_provider)(
                request, provider_id
            )
        except Exception:
            return _error_redirect(
                next_url, f"Provider '{provider_id}' is not configured."
            )

        app = getattr(provider, "app", None)
        if not app:
            return _error_redirect(
                next_url, f"No SocialApp configured for '{provider_id}'."
            )

        # Get the OAuth2 adapter
        AdapterClass = _get_oauth2_adapter_class(provider_id)
        oauth2_adapter = AdapterClass(request)

        # Build callback URL (must match the one used in the login view)
        callback_path = reverse("django_auth_kit:oauth_callback", args=[provider_id])
        callback_url = request.build_absolute_uri(callback_path)

        # Exchange authorization code for access token (async)
        try:
            token_data = await self._exchange_code(
                oauth2_adapter, app, code, callback_url
            )
        except Exception as exc:
            return _error_redirect(next_url, f"Token exchange failed: {exc}")

        # Create allauth SocialToken
        token = SocialToken(
            app=app,
            token=token_data.get("access_token", ""),
            token_secret=token_data.get("refresh_token", ""),
        )

        # Let allauth's adapter fetch user profile and build SocialLogin
        # (allauth internals are sync — run in thread pool)
        try:
            sociallogin = await sync_to_async(oauth2_adapter.complete_login)(
                request, app, token, response=token_data
            )
        except Exception as exc:
            return _error_redirect(next_url, f"Login completion failed: {exc}")

        sociallogin.token = token
        sociallogin.state = {"process": "login"}

        # Look up existing user by social account UID or verified email
        await sync_to_async(sociallogin.lookup)()

        # ``is_existing`` runs a ``User.objects.filter(pk=...).exists()`` query
        # under the hood, so it must be resolved in a thread — it's not a
        # plain attribute.
        is_existing = await sync_to_async(lambda: sociallogin.is_existing)()

        if is_existing:
            user = sociallogin.user
            if not user.is_active:
                return _error_redirect(next_url, "Account is disabled.")
        else:
            is_open = await sync_to_async(allauth_adapter.is_open_for_signup)(
                request, sociallogin
            )
            if not is_open:
                return _error_redirect(next_url, "Sign up is currently closed.")
            await sync_to_async(allauth_adapter.save_user)(
                request, sociallogin, form=None
            )
            await sync_to_async(sociallogin.connect)(request, sociallogin.user)
            user = sociallogin.user

        # Issue JWT tokens
        tokens = JWTService.create_token_pair(user)

        # Redirect to frontend with tokens
        redirect_url = next_url or kit_settings.SOCIAL_LOGIN_REDIRECT_URL()
        if not redirect_url:
            return HttpResponseBadRequest(
                "No redirect URL configured. "
                "Set AUTH_KIT['SOCIAL_LOGIN_REDIRECT_URL'] or pass ?next=..."
            )

        params = urlencode(
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            }
        )
        separator = "&" if "?" in redirect_url else "?"
        return HttpResponseRedirect(f"{redirect_url}{separator}{params}")

    async def _exchange_code(self, oauth2_adapter, app, code, redirect_uri):
        """Exchange authorization code for access token via async POST."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": app.client_id,
            "client_secret": app.secret,
        }

        # Resolve the token URL in a thread because, for some providers (e.g.
        # Microsoft), ``access_token_url`` is a property that queries the DB
        # for the tenant-scoped URL.
        access_token_url = await sync_to_async(
            lambda: oauth2_adapter.access_token_url
        )()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                access_token_url,
                data=data,
                headers={"Accept": "application/json"},
                timeout=15,
            )

        if not resp.is_success:
            try:
                error_body = resp.json()
                error_msg = error_body.get(
                    "error_description",
                    error_body.get("error", resp.text),
                )
            except Exception:
                error_msg = resp.text
            raise ValueError(error_msg)

        return resp.json()
