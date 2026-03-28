# Django Auth Kit

A batteries-included Django authentication package with Strawberry GraphQL, JWT tokens, OTP verification, and optional social login via django-allauth.

## Features

- **UserEmail & UserMobile models** with `is_verified` / `is_primary` support (bring your own User model)
- **OTP verification** via email (Django email backend) and SMS (pluggable backend)
- **JWT authentication** with access + refresh token pairs
- **Strawberry GraphQL API** for all auth operations
- **Social login** via django-allauth (Google, Facebook, Apple, Microsoft, Azure)
- **WSGI & ASGI** support, including Django Channels consumers
- **Fully configurable** via a single `AUTH_KIT` dict in Django settings

## Installation

```bash
pip install django-auth-kit

# With social login support
pip install django-auth-kit[social]

# With Django Channels support
pip install django-auth-kit[channels]
```

## Quick Start

### 1. Add to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    # ...
    "django_auth_kit",
]
```

### 2. Add middleware and include URLs

**Option A: WSGI (or ASGI without Channels)**

```python
MIDDLEWARE = [
    # ...
    "django_auth_kit.middleware.JWTAuthenticationMiddleware",
]
```

```python
# urls.py — WSGI
urlpatterns = [
    path("auth/", include("django_auth_kit.urls")),
]

# urls.py — ASGI (AsyncGraphQLView, no Channels)
from django_auth_kit.urls import async_urlpatterns

urlpatterns = [
    path("auth/", include((async_urlpatterns, "django_auth_kit"))),
]
```

**Option B: Django Channels (recommended for ASGI)**

No Django middleware needed — authentication happens at the consumer level.

```python
# asgi.py
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

See [docs/channels.md](docs/channels.md) for the full Channels setup guide.

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Configure (optional)

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
| `updateProfile` | Yes | Update first/last name |
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
uv sync
uv run pytest
```

## License

MIT
