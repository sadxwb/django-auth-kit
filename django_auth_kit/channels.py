"""
Channels integration for django-auth-kit.

Provides:
- ``GraphQLHTTPConsumer``: Strawberry Channels HTTP consumer with JWT auth.
- ``GraphQLWSConsumer``: Strawberry Channels WebSocket consumer with JWT auth
  for GraphQL subscriptions.
- ``channels_jwt_middleware``: ASGI scope-level JWT middleware for Channels.

Usage (consumer-level auth — recommended)::

    from django_auth_kit.channels import GraphQLHTTPConsumer, GraphQLWSConsumer

    application = ProtocolTypeRouter({
        "http": URLRouter([
            re_path(r"^graphql", GraphQLHTTPConsumer.as_asgi(schema=schema)),
            re_path(r"^", django_asgi_application),
        ]),
        "websocket": URLRouter([
            re_path(r"^graphql", GraphQLWSConsumer.as_asgi(schema=schema)),
        ]),
    })

Usage (scope-level middleware)::

    from django_auth_kit.channels import channels_jwt_middleware

    application = ProtocolTypeRouter({
        "http": URLRouter([
            re_path(
                r"^graphql",
                channels_jwt_middleware(
                    GraphQLHTTPConsumer.as_asgi(schema=schema),
                ),
            ),
        ]),
    })
"""

from __future__ import annotations

import logging

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from strawberry.channels import (
    GraphQLHTTPConsumer as _GraphQLHTTPConsumer,
    ChannelsRequest,
)
from strawberry.channels import GraphQLWSConsumer as _GraphQLWSConsumer
from strawberry.http.typevars import Context, RootValue, SubResponse
from strawberry.types import ExecutionResult, SubscriptionExecutionResult

from django_auth_kit.jwt.service import JWTService

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_token(token: str):
    """Decode a JWT access token and return the user instance."""
    payload = JWTService.decode_token(token)
    if payload.get("type") != "access":
        return None
    User = get_user_model()
    try:
        return User.objects.get(pk=payload["sub"], is_active=True)
    except User.DoesNotExist:
        return None


def _extract_bearer_token(headers: dict[str, str]) -> str | None:
    """Extract Bearer token from authorization header."""
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        return token or None
    return None


class GraphQLHTTPConsumer(_GraphQLHTTPConsumer):
    """
    Strawberry Channels HTTP consumer with built-in JWT authentication.

    Authenticates at ``execute_operation`` time and injects the user into
    ``self.scope["user"]``, ``request.user``, and ``context["user"]``.
    """

    async def execute_operation(
        self,
        request: ChannelsRequest,
        context: Context,
        root_value: RootValue | None,
        sub_response: SubResponse,
    ) -> ExecutionResult | list[ExecutionResult] | SubscriptionExecutionResult:
        token = _extract_bearer_token(request.headers)
        if token:
            try:
                user = await _get_user_from_token(token)
            except Exception as e:
                logger.warning("JWT authentication failed: %s", e)
                user = None

            if user is not None:
                self.scope["user"] = user
                request.user = user

                if isinstance(context, dict):
                    context["user"] = user
                    context["request"] = request

        # If no auth succeeded, propagate scope user (e.g. from AuthMiddlewareStack)
        if isinstance(context, dict) and "user" not in context:
            if "user" in self.scope:
                context["user"] = self.scope["user"]
            elif hasattr(request, "scope") and "user" in request.scope:
                context["user"] = request.scope["user"]

        return await super().execute_operation(
            request, context, root_value, sub_response
        )


class GraphQLWSConsumer(_GraphQLWSConsumer):
    """
    Strawberry Channels WebSocket consumer with JWT authentication
    for GraphQL subscriptions.

    Clients send their JWT in the ``connection_init`` payload::

        {"type": "connection_init", "payload": {"token": "<jwt>"}}

    The token is verified during ``on_ws_connect``.  If valid, the
    resolved user is placed into ``context["user"]`` where
    ``get_current_user()`` already looks for it.
    """

    async def on_ws_connect(self, context):
        params = context.get("connection_params") or {}
        token = params.get("token")

        if not token:
            context["user"] = AnonymousUser()
            return

        try:
            user = await _get_user_from_token(token)
        except Exception as e:
            logger.warning("WebSocket JWT authentication failed: %s", e)
            user = None

        if user is not None:
            context["user"] = user
        else:
            context["user"] = AnonymousUser()


class channels_jwt_middleware:
    """
    ASGI scope-level middleware that decodes a JWT Bearer token from
    the request headers and injects the user into ``scope["user"]``.

    Runs before the consumer, so the user is available in
    ``AuthMiddlewareStack``-style scope access.

    Usage::

        channels_jwt_middleware(consumer_or_app)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = {
                k.decode(): v.decode()
                for k, v in scope.get("headers", [])
            }
            token = _extract_bearer_token(headers)
            if token:
                try:
                    user = await _get_user_from_token(token)
                except Exception as e:
                    logger.warning("JWT scope middleware authentication failed: %s", e)
                    user = None

                if user is not None:
                    scope["user"] = user

            if "user" not in scope:
                scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
