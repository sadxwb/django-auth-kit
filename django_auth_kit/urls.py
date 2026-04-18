from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from strawberry.django.views import AsyncGraphQLView, GraphQLView

from django_auth_kit.schema.schema import schema
from django_auth_kit.social.views import OAuthCallbackView, OAuthLoginView

app_name = "django_auth_kit"

_social_urlpatterns = [
    path(
        "social/<str:provider_id>/login/",
        OAuthLoginView.as_view(),
        name="oauth_login",
    ),
    path(
        "social/<str:provider_id>/callback/",
        OAuthCallbackView.as_view(),
        name="oauth_callback",
    ),
]

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
    *_social_urlpatterns,
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
    *_social_urlpatterns,
]
