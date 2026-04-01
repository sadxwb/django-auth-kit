# Getting Started

## Installation

```bash
pip install django-auth-kit

# With social login support
pip install django-auth-kit[social]

# With Django Channels support
pip install django-auth-kit[channels]
```

## 1. Add to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    # ...
    "django_auth_kit",
]
```

## 2. Add middleware and include URLs

### Option A: WSGI (or ASGI without Channels)

```python
MIDDLEWARE = [
    # ...
    "django_auth_kit.middleware.JWTAuthenticationMiddleware",
]
```

```python
# urls.py — WSGI
from django.urls import path, include

urlpatterns = [
    path("auth/", include("django_auth_kit.urls")),
]
```

```python
# urls.py — ASGI (AsyncGraphQLView, no Channels)
from django_auth_kit.urls import async_urlpatterns

urlpatterns = [
    path("auth/", include((async_urlpatterns, "django_auth_kit"))),
]
```

### Option B: Django Channels (recommended for ASGI)

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

See the [Django Channels guide](channels.md) for the full setup including WebSocket subscriptions.

## 3. Run migrations

```bash
python manage.py migrate
```

## 4. Configure (optional)

All settings live in a single `AUTH_KIT` dictionary. Every setting has a sensible default — you only need to override what you want to change.

```python
from datetime import timedelta

AUTH_KIT = {
    # JWT
    "JWT_ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "JWT_REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # OTP
    "OTP_LENGTH": 6,
    "OTP_TIMEOUT": 300,
    "OTP_COOLDOWN": 60,

    # Rate limiting (DRF-style rates, per client IP)
    "RATE_LIMITS": {
        "send_otp": "5/min",
        "verify_otp": "5/min",
        "login": "5/min",
        "register": "3/min",
        "forgot_password": "3/min",
        "social_login": "5/min",
        "change_password": "3/min",
        "refresh_token": "10/min",
    },

    # SMS backend
    "SMS_BACKEND": "django_auth_kit.otp.backends.console.ConsoleSmsBackend",

    # Social (requires django-auth-kit[social])
    "SOCIAL_PROVIDERS": [],  # e.g. ["google", "facebook", "apple"]
}
```

See the [Configuration Reference](configuration.md) for all available settings.

## Auth Flows

### Registration

```graphql
# 1. Send OTP
mutation {
  sendOtp(input: {
    identifier: "user@example.com"
    purpose: "register"
    channel: "email"
  }) { success message }
}

# 2. Verify OTP
mutation {
  verifyOtp(input: {
    identifier: "user@example.com"
    purpose: "register"
    code: "123456"
  }) { success message }
}

# 3. Register
mutation {
  register(input: {
    identifier: "user@example.com"
    channel: "email"
    code: "123456"
    password1: "securepass"
    password2: "securepass"
  }) {
    success
    tokens { accessToken refreshToken }
  }
}
```

### Login

```graphql
mutation {
  login(input: {
    identifier: "user@example.com"
    password: "securepass"
  }) {
    success
    tokens { accessToken refreshToken }
  }
}
```

### Forgot Password

```graphql
# 1. Send OTP
mutation {
  sendOtp(input: {
    identifier: "user@example.com"
    purpose: "forgot_password"
    channel: "email"
  }) { success }
}

# 2. Verify OTP
mutation {
  verifyOtp(input: {
    identifier: "user@example.com"
    purpose: "forgot_password"
    code: "123456"
  }) { success }
}

# 3. Reset password
mutation {
  forgotPassword(input: {
    identifier: "user@example.com"
    code: "123456"
    newPassword1: "newpass123"
    newPassword2: "newpass123"
  }) { success }
}
```
