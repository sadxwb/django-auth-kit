from __future__ import annotations

import uuid
from datetime import UTC, datetime

import jwt

from django_auth_kit import settings as kit_settings


class JWTService:
    """Handles JWT access and refresh token creation and verification."""

    @classmethod
    def create_access_token(cls, user) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.pk),
            "iat": now,
            "exp": now + kit_settings.JWT_ACCESS_TOKEN_LIFETIME(),
            "iss": kit_settings.JWT_ISSUER(),
            "jti": uuid.uuid4().hex,
            "type": "access",
            "username": user.username,
        }
        return jwt.encode(
            payload,
            kit_settings.JWT_SECRET_KEY(),
            algorithm=kit_settings.JWT_ALGORITHM(),
        )

    @classmethod
    def create_refresh_token(cls, user) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.pk),
            "iat": now,
            "exp": now + kit_settings.JWT_REFRESH_TOKEN_LIFETIME(),
            "iss": kit_settings.JWT_ISSUER(),
            "jti": uuid.uuid4().hex,
            "type": "refresh",
        }
        return jwt.encode(
            payload,
            kit_settings.JWT_SECRET_KEY(),
            algorithm=kit_settings.JWT_ALGORITHM(),
        )

    @classmethod
    def create_token_pair(cls, user) -> dict[str, str]:
        return {
            "access_token": cls.create_access_token(user),
            "refresh_token": cls.create_refresh_token(user),
        }

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """Decode and validate a JWT token. Raises jwt.exceptions on failure."""
        return jwt.decode(
            token,
            kit_settings.JWT_SECRET_KEY(),
            algorithms=[kit_settings.JWT_ALGORITHM()],
            issuer=kit_settings.JWT_ISSUER(),
        )

    @classmethod
    def refresh_access_token(cls, refresh_token: str, user_loader) -> dict[str, str]:
        """
        Given a valid refresh token and a callable that loads a user by pk,
        return a new token pair.

        Args:
            refresh_token: The refresh JWT string.
            user_loader: Callable(pk) -> User instance or None.

        Returns:
            dict with access_token and refresh_token.

        Raises:
            jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError
        """
        payload = cls.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Token is not a refresh token.")

        user = user_loader(payload["sub"])
        if user is None:
            raise ValueError("User not found.")

        return cls.create_token_pair(user)
