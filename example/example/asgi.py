"""
ASGI config for example project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
# ruff: noqa: E402

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing code that may import models.
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from django_auth_kit.channels import GraphQLHTTPConsumer, GraphQLWSConsumer
from django_auth_kit.schema.schema import schema

application = ProtocolTypeRouter(
    {
        "http": URLRouter(
            [
                re_path(r"^graphql", GraphQLHTTPConsumer.as_asgi(schema=schema)),
                re_path(r"^", django_asgi_application),
            ],
        ),
        "websocket": URLRouter(
            [
                re_path(r"^graphql", GraphQLWSConsumer.as_asgi(schema=schema)),
            ],
        ),
    }
)
