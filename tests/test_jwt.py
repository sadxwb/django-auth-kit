import pytest
from django.contrib.auth import get_user_model

from django_auth_kit.jwt.service import JWTService

User = get_user_model()


@pytest.mark.django_db
class TestJWTService:
    def test_create_access_token(self):
        user = User.objects.create_user(username="testuser", password="testpass123")
        token = JWTService.create_access_token(user)
        assert isinstance(token, str)

        payload = JWTService.decode_token(token)
        assert payload["sub"] == str(user.pk)
        assert payload["type"] == "access"

    def test_create_token_pair(self):
        user = User.objects.create_user(username="pairuser", password="testpass123")
        tokens = JWTService.create_token_pair(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        access_payload = JWTService.decode_token(tokens["access_token"])
        assert access_payload["type"] == "access"

        refresh_payload = JWTService.decode_token(tokens["refresh_token"])
        assert refresh_payload["type"] == "refresh"

    def test_refresh_access_token(self):
        user = User.objects.create_user(username="refreshuser", password="testpass123")
        tokens = JWTService.create_token_pair(user)

        new_tokens = JWTService.refresh_access_token(
            tokens["refresh_token"],
            user_loader=lambda pk: User.objects.filter(pk=pk).first(),
        )
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    def test_refresh_with_access_token_fails(self):
        user = User.objects.create_user(username="failuser", password="testpass123")
        tokens = JWTService.create_token_pair(user)

        with pytest.raises(ValueError, match="not a refresh token"):
            JWTService.refresh_access_token(
                tokens["access_token"],
                user_loader=lambda pk: User.objects.filter(pk=pk).first(),
            )
