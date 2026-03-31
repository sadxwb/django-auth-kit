# Architecture

This is a reusable Django app (`django_auth_kit`) that provides a complete auth system over Strawberry GraphQL. It does **not** ship a User model — it works with any `AUTH_USER_MODEL`.

**Data flow:** Models → Services (JWT, OTP) → GraphQL Mutations → Strawberry Schema

## File Structure

```
django_auth_kit/
├── models.py           # UserEmail, UserMobile (linked to AUTH_USER_MODEL)
├── settings.py         # All config via AUTH_KIT dict; lazy-evaluated functions
├── middleware.py        # JWT Bearer token middleware (sync + async, for WSGI/ASGI without Channels)
├── channels.py         # Django Channels integration: GraphQLHTTPConsumer + channels_jwt_middleware
├── admin.py            # Admin with inline email/mobile
├── urls.py             # GraphQL endpoint (sync urlpatterns + async_urlpatterns)
├── apps.py             # Django app config
├── jwt/
│   └── service.py      # JWTService: create/decode/refresh tokens using PyJWT
├── otp/
│   ├── service.py      # OTPService: generate, send (email/sms), verify via Django cache
│   └── backends/
│       ├── base.py     # BaseSmsBackend (abstract, mirrors Django email backend pattern)
│       └── console.py  # ConsoleSmsBackend (prints to stdout, for dev)
├── schema/
│   ├── types.py        # Strawberry output types (UserType, AuthTokens, AuthResponse, etc.)
│   ├── inputs.py       # Strawberry input types for all mutations
│   ├── queries.py      # `me` query
│   ├── utils.py        # get_current_user / get_authenticated_user (WSGI, ASGI, Channels, WebSocket)
│   ├── schema.py       # Combined Strawberry schema (Query + Mutation)
│   └── mutations/
│       ├── auth.py     # sendOtp, verifyOtp, register, login, refreshToken
│       ├── password.py # changePassword, forgotPassword
│       ├── profile.py  # updateProfile
│       └── social.py   # socialLogin (requires django-allauth)
├── social/
│   └── service.py      # SocialLoginService: bridges GraphQL to allauth's provider infrastructure
├── templates/
│   └── django_auth_kit/
│       ├── otp_email.html
│       └── otp_email.txt
└── migrations/
```

## Key Design Decisions

- **No bundled User model**: The package provides `UserEmail` and `UserMobile` models linked to `AUTH_USER_MODEL` via ForeignKey. Consuming projects define their own User model with any extra fields (avatar, display_name, etc.).

- **Settings are lazy functions** (`settings.py`): Every config value is a **callable function** (e.g. `JWT_SECRET_KEY()`), not a module-level constant. This avoids import-time access to `django.conf.settings`. All user config lives in a single `AUTH_KIT` dict in Django settings.

- **OTP is cache-based**: No extra database table. OTPs are stored in Django's cache framework with TTL, making the system stateless and backend-agnostic. Cache keys follow the pattern `authkit:otp:{purpose}:{identifier}`. Auth flows (register, forgot-password) require `sendOtp → verifyOtp → action`, with the verified state also tracked in cache.

- **SMS backend pattern**: Mirrors Django's email backend (`BaseSmsBackend` with `send_messages()`). Users subclass it to integrate Twilio, AWS SNS, etc. Configured via `AUTH_KIT["SMS_BACKEND"]`.

- **Two deployment modes**:
  - **WSGI / simple ASGI**: Use `JWTAuthenticationMiddleware` in Django `MIDDLEWARE` + URL-based views (`urlpatterns` or `async_urlpatterns`).
  - **Django Channels ASGI**: Use `GraphQLHTTPConsumer` (authenticates at `execute_operation` time) or `channels_jwt_middleware` (ASGI scope-level). No Django middleware needed — auth happens at the consumer/scope level where it has access to `scope["user"]`, `request.user`, and `context["user"]`.

- **User resolution in resolvers** (`schema/utils.py`): `get_current_user(info)` follows a multi-location fallback matching strawberry_django's pattern:
  1. `context["user"]` — set by `GraphQLHTTPConsumer.execute_operation` (Channels)
  2. `request.user` — set by Django middleware (WSGI / ASGI HTTP)
  3. `request.consumer.scope["user"]` — ASGI queries/mutations via Channels
  4. `request.scope["user"]` — WebSocket subscriptions

- **Social login is optional**: Gated behind `try/except ImportError` in the mutation. Requires `pip install django-auth-kit[social]`. Delegates entirely to allauth's `provider.verify_token()` for token verification and `adapter.save_user()` for user creation — no provider-specific code in django-auth-kit itself. Any allauth provider with `supports_token_authentication = True` works automatically.

- **GraphQL schema composition**: `schema/schema.py` combines `Query` with multiple mutation classes via multiple inheritance: `Mutation(AuthMutation, PasswordMutation, ProfileMutation, SocialMutation)`. To add a mutation, create a new class in `schema/mutations/` and add it to the bases.

## Tech Stack

- **Django** >= 5.2
- **Strawberry GraphQL** + strawberry-graphql-django
- **PyJWT** for token encoding/decoding
- **Django Channels** (optional) for ASGI consumer-based deployments
- **django-allauth** (optional) for social providers
