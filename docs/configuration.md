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

OTP emails are sent using Django's built-in email backend. Configure `EMAIL_BACKEND`, `EMAIL_HOST`, etc. in your Django settings as usual.

## Profile Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ME_QUERY_FIELDS` | `list[str]` | `["first_name", "last_name", "avatar", "display_name"]` | Fields returned by the `me` query |
| `UPDATE_PROFILE_FIELDS` | `list[str]` | `["first_name", "last_name", "avatar", "display_name"]` | Fields allowed in `updateProfile` mutation |

## Social Login Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `SOCIAL_PROVIDERS` | `list[str]` | `[]` | Enabled social providers (e.g. `["google", "facebook"]`) |

Social login requires the `social` extra:

```bash
pip install django-auth-kit[social]
```

See the [Social Login guide](social-login.md) for full setup instructions.
