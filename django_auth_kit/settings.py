from datetime import timedelta

from django.conf import settings


class _Default:
    """Sentinel for unset values."""

    pass


_DEFAULT = _Default()


def get_setting(name: str, default=_DEFAULT):
    auth_kit_settings = getattr(settings, "AUTH_KIT", {})
    if name in auth_kit_settings:
        return auth_kit_settings[name]
    if isinstance(default, _Default):
        raise KeyError(f"AUTH_KIT['{name}'] is required but not set.")
    return default


# --- JWT ---


def JWT_SECRET_KEY():
    return get_setting("JWT_SECRET_KEY", settings.SECRET_KEY)


def JWT_ALGORITHM():
    return get_setting("JWT_ALGORITHM", "HS256")


def JWT_ACCESS_TOKEN_LIFETIME():
    return get_setting("JWT_ACCESS_TOKEN_LIFETIME", timedelta(hours=1))


def JWT_REFRESH_TOKEN_LIFETIME():
    return get_setting("JWT_REFRESH_TOKEN_LIFETIME", timedelta(days=7))


def JWT_ISSUER():
    return get_setting("JWT_ISSUER", "django-auth-kit")


# --- OTP ---


def OTP_LENGTH():
    return get_setting("OTP_LENGTH", 6)


def OTP_TIMEOUT():
    return get_setting("OTP_TIMEOUT", 300)  # seconds


def OTP_MAX_ATTEMPTS():
    return get_setting("OTP_MAX_ATTEMPTS", 5)


def OTP_COOLDOWN():
    return get_setting("OTP_COOLDOWN", 60)  # seconds between sends


# --- SMS ---


def SMS_BACKEND():
    return get_setting(
        "SMS_BACKEND", "django_auth_kit.otp.backends.console.ConsoleSmsBackend"
    )


# --- Social providers (list of enabled provider keys) ---


def SOCIAL_PROVIDERS():
    return get_setting("SOCIAL_PROVIDERS", [])


def SOCIAL_LOGIN_REDIRECT_URL():
    """Frontend URL to redirect to after OAuth login."""
    return get_setting("SOCIAL_LOGIN_REDIRECT_URL", "")


# --- Rate Limiting ---


def RATE_LIMITS():
    return get_setting(
        "RATE_LIMITS",
        {
            "send_otp": "5/min",
            "verify_otp": "5/min",
            "login": "5/min",
            "register": "3/min",
            "forgot_password": "3/min",
            "social_login": "5/min",
            "change_password": "3/min",
            "refresh_token": "10/min",
        },
    )


# --- User Profile Fields ---


def EXTRA_USER_PROFILE_FIELDS():
    """Additional user model fields to include alongside the defaults."""
    return get_setting("EXTRA_USER_PROFILE_FIELDS", [])


# --- Email ---


def OTP_EMAIL_SUBJECT():
    return get_setting("OTP_EMAIL_SUBJECT", "Your verification code")


def OTP_EMAIL_FROM():
    return get_setting(
        "OTP_EMAIL_FROM", getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
    )


# --- Invitation ---


def INVITATION_EMAIL_SUBJECT():
    return get_setting("INVITATION_EMAIL_SUBJECT", "You've been invited")


def INVITATION_TOKEN_MAX_AGE():
    """Lifetime (seconds) of an invitation token. Default 7 days."""
    return get_setting("INVITATION_TOKEN_MAX_AGE", 60 * 60 * 24 * 7)


def INVITATION_REDIRECT_URL():
    """Frontend URL the invitation link points at (token is appended as ?token=)."""
    return get_setting("INVITATION_REDIRECT_URL", "")
