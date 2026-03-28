# Django Channels Integration

Django Auth Kit provides first-class support for [Django Channels](https://channels.readthedocs.io/) ASGI deployments. When using Channels, authentication happens at the consumer or ASGI scope level instead of Django middleware.

## Installation

```bash
pip install django-auth-kit[channels]
```

## Setup

There are two approaches — choose based on your needs.

### Option A: Consumer-level auth (recommended)

`GraphQLHTTPConsumer` extends Strawberry's Channels HTTP consumer. It decodes the JWT Bearer token in `execute_operation` and injects the authenticated user into `scope["user"]`, `request.user`, and `context["user"]`.

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from django_auth_kit.channels import GraphQLHTTPConsumer
from myproject.schema import schema

application = ProtocolTypeRouter({
    "http": URLRouter([
        re_path(r"^graphql", GraphQLHTTPConsumer.as_asgi(schema=schema)),
        re_path(r"^", django_asgi_application),
    ]),
})
```

This is the simplest approach — no extra middleware needed. The consumer handles auth internally.

### Option B: Scope-level middleware

`channels_jwt_middleware` is an ASGI middleware that runs before the consumer. It decodes the JWT from the `Authorization` header and sets `scope["user"]`. This is useful when you want auth to happen once at the scope level and have multiple consumers share the result, or when composing with other ASGI middleware.

```python
# asgi.py
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from django_auth_kit.channels import GraphQLHTTPConsumer, channels_jwt_middleware

application = ProtocolTypeRouter({
    "http": URLRouter([
        re_path(
            r"^graphql",
            channels_jwt_middleware(
                GraphQLHTTPConsumer.as_asgi(schema=schema),
            ),
        ),
        re_path(r"^", django_asgi_application),
    ]),
})
```

You can also compose it with `AuthMiddlewareStack` and other middleware:

```python
re_path(
    r"^graphql",
    AuthMiddlewareStack(
        channels_jwt_middleware(
            GraphQLHTTPConsumer.as_asgi(schema=schema),
        ),
    ),
),
```

## Custom consumer

To add custom behavior (extra headers, logging, etc.), subclass `GraphQLHTTPConsumer`:

```python
from django_auth_kit.channels import GraphQLHTTPConsumer as _GraphQLHTTPConsumer

class GraphQLHTTPConsumer(_GraphQLHTTPConsumer):
    async def execute_operation(self, request, context, root_value, sub_response):
        # Call super to handle JWT auth
        result = await super().execute_operation(request, context, root_value, sub_response)

        # Add custom context from headers
        if isinstance(context, dict):
            if org_ref := request.headers.get("x-organization-ref"):
                context["x-organization-ref"] = org_ref

        return result
```

## How user resolution works

All GraphQL resolvers use `get_current_user(info)` from `django_auth_kit.schema.utils` to access the authenticated user. This function checks multiple locations in order:

1. `info.context["user"]` — set by `GraphQLHTTPConsumer.execute_operation`
2. `request.user` — set by Django middleware (WSGI / ASGI without Channels)
3. `request.consumer.scope["user"]` — ASGI consumer scope (Channels HTTP)
4. `request.scope["user"]` — WebSocket scope (Channels subscriptions)

This means resolvers work transparently across WSGI, ASGI, and Channels deployments without any code changes.

## Important notes

- **Do not add `JWTAuthenticationMiddleware` to Django `MIDDLEWARE`** when using Channels consumers. Django middleware does not run for Channels requests. The consumer handles auth directly.
- **Cache backend**: OTP verification requires a shared cache backend (e.g. Redis) in production. `LocMemCache` is per-process and will not work across multiple workers.
- **`channels` is an optional dependency**: The `django_auth_kit.channels` module is only importable when `channels` is installed.
