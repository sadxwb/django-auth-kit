from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import AsyncGraphQLView, GraphQLView

from django_auth_kit.schema.schema import schema

app_name = "django_auth_kit"

urlpatterns = [
    path(
        "graphql/",
        csrf_exempt(
            GraphQLView.as_view(
                schema=schema,
                multipart_uploads_enabled=True,
            )
        ),
        name="graphql",
    ),
]

# Async URL patterns for ASGI deployments.
# Usage: include("django_auth_kit.urls_async") or import async_urlpatterns directly.
async_urlpatterns = [
    path(
        "graphql/",
        csrf_exempt(
            AsyncGraphQLView.as_view(
                schema=schema,
                multipart_uploads_enabled=True,
            )
        ),
        name="graphql",
    ),
]
