from __future__ import annotations

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils.decorators import sync_and_async_middleware

from django_auth_kit.jwt.service import JWTService


def _authenticate(request):
    """Extract JWT from Authorization header and set request.user."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return

    token = auth_header[7:]
    try:
        payload = JWTService.decode_token(token)
    except Exception:
        return

    if payload.get("type") != "access":
        return

    User = get_user_model()
    try:
        request.user = User.objects.get(pk=payload["sub"], is_active=True)
    except User.DoesNotExist:
        request.user = AnonymousUser()


@sync_and_async_middleware
def JWTAuthenticationMiddleware(get_response):
    """
    Middleware that authenticates requests using JWT Bearer tokens.

    Supports both WSGI and ASGI (sync and async) request handling.
    """
    if iscoroutinefunction(get_response):

        async def middleware(request):
            await sync_to_async(_authenticate)(request)
            return await get_response(request)

    else:

        def middleware(request):
            _authenticate(request)
            return get_response(request)

    return middleware
