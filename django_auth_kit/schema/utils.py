from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from strawberry.types import Info


def get_request(info: Info):
    """Return the request from Info for both WSGI and ASGI."""
    try:
        return info.context.request
    except AttributeError:
        return info.context.get("request")


def get_current_user(info: Info):
    """
    Get the current user from a Strawberry Info context.

    Resolution order (mirrors strawberry_django + Channels consumer pattern):
    1. context["user"] (set by GraphQLHTTPConsumer.execute_operation)
    2. request.user (WSGI / ASGI HTTP via Django middleware)
    3. request.consumer.scope["user"] (ASGI queries/mutations via Channels)
    4. request.scope["user"] (WebSocket subscriptions)
    """
    # Check dict-style context first (Channels consumers inject user here)
    if isinstance(info.context, dict):
        user = info.context.get("user")
        if user is not None:
            return user

    request = get_request(info)
    if request is None:
        return AnonymousUser()

    try:
        user = request.user
    except AttributeError:
        try:
            # ASGI queries/mutations move the user into consumer scope
            user = request.consumer.scope["user"]
        except (AttributeError, KeyError):
            try:
                # WebSocket subscriptions put scope directly on the request
                user = request.scope.get("user")
            except AttributeError:
                user = None

    if user is None:
        return AnonymousUser()

    return user


def get_authenticated_user(info: Info):
    """Get the current user, raising PermissionError if not authenticated."""
    user = get_current_user(info)
    if not user.is_authenticated:
        raise PermissionError("Authentication required.")
    return user
