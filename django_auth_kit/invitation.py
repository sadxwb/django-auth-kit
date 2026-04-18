"""
Admin-invitation flow: an admin creates a user, the user gets an emailed
signed link, clicks it, chooses a password, and is logged in with a JWT.

Token is a ``TimestampSigner`` payload of ``"<user_pk>:<primary_email>"``.
Including the email invalidates the token if the user's email is changed
before the invitee accepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template.loader import render_to_string

from django_auth_kit import settings as kit_settings
from django_auth_kit.models import UserEmail

_SALT = "django_auth_kit.invitation"


@dataclass(frozen=True)
class _InvitationPayload:
    user_pk: str
    email: str


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=_SALT)


def generate_invitation_token(user, email: str) -> str:
    """Return a signed token for the given user + email."""
    return _signer().sign(f"{user.pk}:{email}")


def decode_invitation_token(
    token: str, max_age: int | None = None
) -> _InvitationPayload:
    """
    Verify a token and return its payload. Raises ``BadSignature`` (or
    subclass ``SignatureExpired``) on failure.
    """
    if max_age is None:
        max_age = kit_settings.INVITATION_TOKEN_MAX_AGE()
    raw = _signer().unsign(token, max_age=max_age)
    pk, _, email = raw.partition(":")
    if not pk or not email:
        raise BadSignature("Malformed invitation token.")
    return _InvitationPayload(user_pk=pk, email=email)


def send_invitation_email(
    user,
    frontend_url: str | None = None,
    inviter=None,
    email: str | None = None,
) -> str:
    """
    Generate an invitation link and email it to ``user``.

    Resolves the email from ``email`` kwarg, else the user's primary
    ``UserEmail`` row, else ``user.email``. Returns the full link that was
    sent (useful for tests and admin audit logs).
    """
    resolved_email = (
        email
        or _primary_email(user)
        or getattr(user, "email", "")
    )
    if not resolved_email:
        raise ValueError("User has no email address to invite.")

    token = generate_invitation_token(user, resolved_email)

    base = (frontend_url or kit_settings.INVITATION_REDIRECT_URL()).rstrip("/")
    if not base:
        raise ValueError(
            "No invitation redirect URL configured. Pass frontend_url or set "
            "AUTH_KIT['INVITATION_REDIRECT_URL']."
        )
    link = f"{base}?{urlencode({'token': token})}"

    context = {
        "user": user,
        "email": resolved_email,
        "link": link,
        "inviter": inviter,
    }
    text_body = render_to_string("django_auth_kit/invitation_email.txt", context)
    html_body = render_to_string("django_auth_kit/invitation_email.html", context)

    send_mail(
        subject=kit_settings.INVITATION_EMAIL_SUBJECT(),
        message=text_body,
        from_email=kit_settings.OTP_EMAIL_FROM(),
        recipient_list=[resolved_email],
        html_message=html_body,
    )
    return link


def _primary_email(user) -> str | None:
    row = UserEmail.objects.filter(user=user, is_primary=True).only("email").first()
    return row.email if row else None
