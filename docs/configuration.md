
# Configuration

All settings are configured via the `AUTH_KIT` dictionary in your Django `settings.py`.

```python
AUTH_KIT = {
    # ...
}
```

Every setting has a sensible default. You only need to override what you want to change.

## JWT Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `JWT_SECRET_KEY` | `str` | `SECRET_KEY` | Key used to sign JWT tokens |
| `JWT_ALGORITHM` | `str` | `"HS256"` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_LIFETIME` | `timedelta` | `1 hour` | Access token expiry |
| `JWT_REFRESH_TOKEN_LIFETIME` | `timedelta` | `7 days` | Refresh token expiry |
| `JWT_ISSUER` | `str` | `"django-auth-kit"` | Value of the `iss` claim |

## OTP Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `OTP_LENGTH` | `int` | `6` | Number of digits in the OTP code |
| `OTP_TIMEOUT` | `int` | `300` | Seconds before OTP expires |
| `OTP_MAX_ATTEMPTS` | `int` | `5` | Max verification attempts before lockout |
| `OTP_COOLDOWN` | `int` | `60` | Seconds between OTP send requests |

## SMS Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `SMS_BACKEND` | `str` | `"django_auth_kit.otp.backends.console.ConsoleSmsBackend"` | Dotted path to the SMS backend class |

## Email Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `OTP_EMAIL_SUBJECT` | `str` | `"Your verification code"` | Subject line for OTP emails |
| `OTP_EMAIL_FROM` | `str` | `DEFAULT_FROM_EMAIL` | Sender address for OTP emails |

OTP emails are sent via Django's `send_mail()`, which respects Django's `EMAIL_BACKEND` setting. To use a provider like Microsoft 365 or Amazon SES, install the appropriate Django email backend package (e.g. `django-o365-mail`, `django-ses`) and configure `EMAIL_BACKEND` in your Django settings.

## Rate Limiting

Rate limiting uses DRF-style rate strings and is applied per client IP via Django's cache framework. Every mutation has a sensible default; set a key to `None` to disable limiting for that action.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `RATE_LIMITS` | `dict` | *(see below)* | Per-action rate limits |

Default `RATE_LIMITS`:

```python
AUTH_KIT = {
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
}
```

Rate format: `"<number>/<period>"` where period is one of `s`, `sec`, `m`, `min`, `h`, `hour`, `d`, `day`.

To disable rate limiting entirely:

```python
AUTH_KIT = {
    "RATE_LIMITS": {},
}
```

To override a single action:

```python
AUTH_KIT = {
    "RATE_LIMITS": {
        "send_otp": "10/hour",
        "verify_otp": "5/min",
        "login": "10/min",
        "register": "3/min",
        "forgot_password": "3/min",
        "social_login": "5/min",
        "change_password": "3/min",
        "refresh_token": "10/min",
    },
}
```

> **Note:** Rate limiting uses Django's cache. For production, configure a persistent cache backend like Redis.

## Social Login Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `SOCIAL_PROVIDERS` | `list[str]` | `[]` | Enabled social providers (e.g. `["google", "facebook"]`) |

Social login requires the `social` extra:

```bash
pip install django-auth-kit[social]
```

See the [Social Login guide](social-login.md) for full setup instructions.
