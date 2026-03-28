# Architecture

This is a reusable Django app (`django_auth_kit`) that provides a complete auth system over Strawberry GraphQL.

**Data flow:** Models → Services (JWT, OTP) → GraphQL Mutations → Strawberry Schema

## File Structure

```
django_auth_kit/
├── models.py           # User (extends AbstractUser), UserEmail, UserMobile
├── settings.py         # All config via AUTH_KIT dict; lazy-evaluated functions
├── middleware.py        # JWT Bearer token middleware (sync + async)
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
│   ├── schema.py       # Combined Strawberry schema (Query + Mutation)
│   └── mutations/
│       ├── auth.py     # sendOtp, verifyOtp, register, login, refreshToken
│       ├── password.py # changePassword, forgotPassword
│       ├── profile.py  # updateProfile
│       └── social.py   # socialLogin (requires django-allauth)
├── social/             # Reserved for social login extensions
├── templates/
│   └── django_auth_kit/
│       ├── otp_email.html
│       └── otp_email.txt
└── migrations/
```

## Key Design Decisions

- **Settings are lazy functions** (`settings.py`): Every config value is a **callable function** (e.g. `JWT_SECRET_KEY()`), not a module-level constant. This avoids import-time access to `django.conf.settings`. All user config lives in a single `AUTH_KIT` dict in Django settings.

- **OTP is cache-based**: No extra database table. OTPs are stored in Django's cache framework with TTL, making the system stateless and backend-agnostic. Cache keys follow the pattern `authkit:otp:{purpose}:{identifier}`. Auth flows (register, forgot-password) require `sendOtp → verifyOtp → action`, with the verified state also tracked in cache.

- **SMS backend pattern**: Mirrors Django's email backend (`BaseSmsBackend` with `send_messages()`). Users subclass it to integrate Twilio, AWS SNS, etc. Configured via `AUTH_KIT["SMS_BACKEND"]`.

- **WSGI + ASGI**: The JWT middleware uses `@sync_and_async_middleware` to handle both. URLs export `urlpatterns` (sync `GraphQLView`) and `async_urlpatterns` (async `AsyncGraphQLView`).

- **Social login is optional**: Gated behind `try/except ImportError` in the mutation. Requires `pip install django-auth-kit[social]`. Provider user-info URLs are in `_fetch_provider_user()` in `schema/mutations/social.py`.

- **GraphQL schema composition**: `schema/schema.py` combines `Query` with multiple mutation classes via multiple inheritance: `Mutation(AuthMutation, PasswordMutation, ProfileMutation, SocialMutation)`. To add a mutation, create a new class in `schema/mutations/` and add it to the bases.

## Tech Stack

- **Django** >= 4.2
- **Strawberry GraphQL** + strawberry-graphql-django
- **PyJWT** for token encoding/decoding
- **django-allauth** (optional) for social providers
