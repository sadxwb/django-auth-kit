# Django Auth Kit

A batteries-included Django authentication package with Strawberry GraphQL, JWT tokens, OTP verification, and optional social login via django-allauth.

## Features

- **Extended User model** with avatar and display name
- **Email & Mobile models** with `is_verified` / `is_primary` support
- **OTP verification** via email (Django email backend) and SMS (pluggable backend)
- **JWT authentication** with access + refresh token pairs
- **Strawberry GraphQL API** for all auth operations
- **Social login** via django-allauth (Google, Facebook, Apple, Microsoft, Azure)
- **WSGI & ASGI** support out of the box
- **Fully configurable** via a single `AUTH_KIT` dict in Django settings

## Installation

```bash
pip install django-auth-kit

# With social login support
pip install django-auth-kit[social]
```

## Quick Start

### 1. Add to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    # ...
    "django_auth_kit",
]
```

### 2. Set `AUTH_USER_MODEL`

```python
AUTH_USER_MODEL = "django_auth_kit.User"
```

### 3. Add middleware

```python
MIDDLEWARE = [
    # ...
    "django_auth_kit.middleware.JWTAuthenticationMiddleware",
]
```

### 4. Include URLs

```python
# WSGI
from django.urls import include, path

urlpatterns = [
    path("auth/", include("django_auth_kit.urls")),
]
```

```python
# ASGI
from django.urls import include, path
from django_auth_kit.urls import async_urlpatterns

urlpatterns = [
    path("auth/", include((async_urlpatterns, "django_auth_kit"))),
]
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Configure (optional)

```python
from datetime import timedelta

AUTH_KIT = {
    # JWT
    "JWT_SECRET_KEY": SECRET_KEY,               # default: SECRET_KEY
    "JWT_ALGORITHM": "HS256",                   # default: "HS256"
    "JWT_ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "JWT_REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "JWT_ISSUER": "django-auth-kit",

    # OTP
    "OTP_LENGTH": 6,
    "OTP_TIMEOUT": 300,                         # seconds
    "OTP_MAX_ATTEMPTS": 5,
    "OTP_COOLDOWN": 60,                         # seconds between sends

    # SMS backend
    "SMS_BACKEND": "django_auth_kit.otp.backends.console.ConsoleSmsBackend",

    # Email
    "OTP_EMAIL_SUBJECT": "Your verification code",
    "OTP_EMAIL_FROM": "noreply@example.com",

    # Profile
    "ME_QUERY_FIELDS": ["first_name", "last_name", "avatar", "display_name"],
    "UPDATE_PROFILE_FIELDS": ["first_name", "last_name", "avatar", "display_name"],

    # Social (requires django-auth-kit[social])
    "SOCIAL_PROVIDERS": [],  # e.g. ["google", "facebook", "apple"]
}
```

## GraphQL API

The GraphQL endpoint is available at `/auth/graphql/` (or wherever you mount the URLs). Open it in a browser to access the GraphiQL IDE.

### Queries

| Query | Auth Required | Description |
|-------|---------------|-------------|
| `me` | Yes | Returns the authenticated user's profile |

### Mutations

| Mutation | Auth Required | Description |
|----------|---------------|-------------|
| `sendOtp` | No | Send an OTP code to an email or mobile |
| `verifyOtp` | No | Verify an OTP code |
| `register` | No | Register with verified OTP + password |
| `login` | No | Login with email/mobile + password |
| `refreshToken` | No | Get a new token pair from a refresh token |
| `changePassword` | Yes | Change password (requires current password) |
| `forgotPassword` | No | Reset password with verified OTP |
| `updateProfile` | Yes | Update profile fields and avatar |
| `socialLogin` | No | Authenticate via a social provider |

### Auth Flows

**Registration:**
```graphql
# 1. Send OTP
mutation { sendOtp(input: { identifier: "user@example.com", purpose: "register", channel: "email" }) { success message } }

# 2. Verify OTP
mutation { verifyOtp(input: { identifier: "user@example.com", purpose: "register", code: "123456" }) { success message } }

# 3. Register
mutation { register(input: { identifier: "user@example.com", channel: "email", code: "123456", password1: "securepass", password2: "securepass" }) { success tokens { accessToken refreshToken } } }
```

**Login:**
```graphql
mutation { login(input: { identifier: "user@example.com", password: "securepass" }) { success tokens { accessToken refreshToken } } }
```

**Forgot Password:**
```graphql
# 1. Send OTP
mutation { sendOtp(input: { identifier: "user@example.com", purpose: "forgot_password", channel: "email" }) { success } }

# 2. Verify OTP
mutation { verifyOtp(input: { identifier: "user@example.com", purpose: "forgot_password", code: "123456" }) { success } }

# 3. Reset password
mutation { forgotPassword(input: { identifier: "user@example.com", code: "123456", newPassword1: "newpass123", newPassword2: "newpass123" }) { success } }
```

## Custom SMS Backend

Create a backend by subclassing `BaseSmsBackend`:

```python
from django_auth_kit.otp.backends.base import BaseSmsBackend

class TwilioSmsBackend(BaseSmsBackend):
    def send_messages(self, messages):
        sent = 0
        for message in messages:
            for recipient in message.to:
                # Send via Twilio API
                sent += 1
        return sent
```

Then configure:

```python
AUTH_KIT = {
    "SMS_BACKEND": "myapp.sms.TwilioSmsBackend",
}
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT
