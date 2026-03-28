import pytest
from django.contrib.auth import get_user_model

from django_auth_kit.models import UserEmail, UserMobile

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_computed_display_name_from_display_name(self):
        user = User.objects.create_user(
            username="test", password="pass123", display_name="Custom Name"
        )
        assert user.computed_display_name == "Custom Name"

    def test_computed_display_name_from_full_name(self):
        user = User.objects.create_user(
            username="test", password="pass123", first_name="John", last_name="Doe"
        )
        assert user.computed_display_name == "John Doe"

    def test_computed_display_name_fallback_to_username(self):
        user = User.objects.create_user(username="fallback", password="pass123")
        assert user.computed_display_name == "fallback"


@pytest.mark.django_db
class TestUserEmail:
    def test_create_email(self):
        user = User.objects.create_user(username="emailuser", password="pass123")
        email = UserEmail.objects.create(
            user=user, email="test@example.com", is_verified=True, is_primary=True
        )
        assert email.is_primary is True
        assert str(email) == "test@example.com (primary) [verified]"

    def test_only_one_primary(self):
        user = User.objects.create_user(username="multimail", password="pass123")
        e1 = UserEmail.objects.create(
            user=user, email="a@example.com", is_primary=True
        )
        UserEmail.objects.create(user=user, email="b@example.com", is_primary=True)
        e1.refresh_from_db()
        assert e1.is_primary is False


@pytest.mark.django_db
class TestUserMobile:
    def test_create_mobile(self):
        user = User.objects.create_user(username="mobileuser", password="pass123")
        mobile = UserMobile.objects.create(
            user=user, mobile="+1234567890", is_verified=True, is_primary=True
        )
        assert mobile.is_primary is True

    def test_only_one_primary(self):
        user = User.objects.create_user(username="multimob", password="pass123")
        m1 = UserMobile.objects.create(
            user=user, mobile="+111", is_primary=True
        )
        UserMobile.objects.create(user=user, mobile="+222", is_primary=True)
        m1.refresh_from_db()
        assert m1.is_primary is False
