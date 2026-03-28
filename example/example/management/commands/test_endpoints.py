"""
Management command to test all django-auth-kit GraphQL endpoints.

Usage:
    uv run python manage.py test_endpoints

Runs in-process using Django's test client so it can share the
LocMemCache with the OTP service (no running server needed).
"""

import json

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.test import Client

GRAPHQL_URL = "/auth/graphql/"

# Test data
EMAIL = "test@example.com"
PASSWORD = "testpass123"
NEW_PASSWORD = "newpass12345"


class Command(BaseCommand):
    help = "Test all django-auth-kit GraphQL endpoints"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = Client()
        self.access_token = None
        self.refresh_token = None
        self.passed = 0
        self.failed = 0

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  django-auth-kit endpoint tests")
        self.stdout.write("=" * 60 + "\n")

        # Registration flow
        self.test_send_otp_register()
        self.test_verify_otp_register()
        self.test_register()

        # Login
        self.test_login()

        # Authenticated queries/mutations
        self.test_me()
        self.test_update_profile()
        self.test_change_password()

        # Refresh token
        self.test_refresh_token()

        # Forgot password flow
        self.test_send_otp_forgot_password()
        self.test_verify_otp_forgot_password()
        self.test_forgot_password()

        # Login with new password
        self.test_login_new_password()

        # Error cases
        self.test_login_wrong_password()
        self.test_me_unauthenticated()
        self.test_register_duplicate()
        self.test_send_otp_cooldown()

        # Summary
        self.stdout.write("\n" + "=" * 60)
        total = self.passed + self.failed
        self.stdout.write(f"  Results: {self.passed}/{total} passed")
        if self.failed:
            self.stdout.write(
                self.style.ERROR(f"  {self.failed} FAILED")
            )
        else:
            self.stdout.write(self.style.SUCCESS("  All tests passed!"))
        self.stdout.write("=" * 60 + "\n")

    # -- helpers --

    def _gql(self, query, variables=None, token=None):
        headers = {"content_type": "application/json"}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        body = {"query": query}
        if variables:
            body["variables"] = variables
        resp = self.client.post(
            GRAPHQL_URL, json.dumps(body), **headers
        )
        return json.loads(resp.content)

    def _read_otp(self, identifier, purpose):
        """Read OTP directly from cache (same process)."""
        return cache.get(f"authkit:otp:{purpose}:{identifier}")

    def _check(self, name, data, path, expected_value):
        """Navigate a dotted path in data and assert the value."""
        val = data
        for key in path.split("."):
            if isinstance(val, dict):
                val = val.get(key)
            else:
                val = None
                break

        if val == expected_value:
            self.stdout.write(self.style.SUCCESS(f"  PASS  {name}"))
            self.passed += 1
        else:
            self.stdout.write(
                self.style.ERROR(f"  FAIL  {name}")
            )
            self.stdout.write(f"        expected: {expected_value!r}")
            self.stdout.write(f"        got:      {val!r}")
            self.failed += 1

    # -- registration flow --

    def test_send_otp_register(self):
        self.stdout.write("\n--- Registration Flow ---")
        data = self._gql(
            """
            mutation($input: SendOtpInput!) {
                sendOtp(input: $input) { success message }
            }
            """,
            {"input": {"identifier": EMAIL, "purpose": "register", "channel": "email"}},
        )
        self._check("sendOtp (register)", data, "data.sendOtp.success", True)

    def test_verify_otp_register(self):
        otp = self._read_otp(EMAIL, "register")
        data = self._gql(
            """
            mutation($input: VerifyOtpInput!) {
                verifyOtp(input: $input) { success message }
            }
            """,
            {"input": {"identifier": EMAIL, "purpose": "register", "code": otp}},
        )
        self._check("verifyOtp (register)", data, "data.verifyOtp.success", True)

    def test_register(self):
        data = self._gql(
            """
            mutation($input: RegisterInput!) {
                register(input: $input) {
                    success message
                    tokens { accessToken refreshToken }
                    user { id username emails { email isVerified isPrimary } }
                }
            }
            """,
            {
                "input": {
                    "identifier": EMAIL,
                    "channel": "email",
                    "code": "000000",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                    "firstName": "Test",
                    "lastName": "User",
                }
            },
        )
        self._check("register", data, "data.register.success", True)
        tokens = (data.get("data") or {}).get("register") or {}
        token_data = tokens.get("tokens") or {}
        self.access_token = token_data.get("accessToken")
        self.refresh_token = token_data.get("refreshToken")

    # -- login --

    def test_login(self):
        self.stdout.write("\n--- Login ---")
        data = self._gql(
            """
            mutation($input: LoginInput!) {
                login(input: $input) {
                    success message
                    tokens { accessToken refreshToken }
                    user { id username firstName lastName }
                }
            }
            """,
            {"input": {"identifier": EMAIL, "password": PASSWORD}},
        )
        self._check("login", data, "data.login.success", True)
        self._check("login user.firstName", data, "data.login.user.firstName", "Test")
        tokens = (data.get("data") or {}).get("login") or {}
        token_data = tokens.get("tokens") or {}
        self.access_token = token_data.get("accessToken")
        self.refresh_token = token_data.get("refreshToken")

    # -- authenticated endpoints --

    def test_me(self):
        self.stdout.write("\n--- Authenticated Queries ---")
        data = self._gql(
            """
            query { me { id username firstName lastName emails { email isPrimary } } }
            """,
            token=self.access_token,
        )
        self._check("me query", data, "data.me.username", EMAIL)
        self._check("me firstName", data, "data.me.firstName", "Test")

    def test_update_profile(self):
        data = self._gql(
            """
            mutation($input: UpdateProfileInput!) {
                updateProfile(input: $input) {
                    success message
                    user { firstName lastName }
                }
            }
            """,
            {"input": {"firstName": "Updated", "lastName": "Name"}},
            token=self.access_token,
        )
        self._check("updateProfile", data, "data.updateProfile.success", True)
        self._check(
            "updateProfile firstName",
            data,
            "data.updateProfile.user.firstName",
            "Updated",
        )

    def test_change_password(self):
        data = self._gql(
            """
            mutation($input: ChangePasswordInput!) {
                changePassword(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "oldPassword": PASSWORD,
                    "newPassword1": NEW_PASSWORD,
                    "newPassword2": NEW_PASSWORD,
                }
            },
            token=self.access_token,
        )
        self._check("changePassword", data, "data.changePassword.success", True)

    # -- refresh token --

    def test_refresh_token(self):
        self.stdout.write("\n--- Token Refresh ---")
        data = self._gql(
            """
            mutation($input: RefreshTokenInput!) {
                refreshToken(input: $input) {
                    success message
                    tokens { accessToken refreshToken }
                }
            }
            """,
            {"input": {"refreshToken": self.refresh_token}},
        )
        self._check("refreshToken", data, "data.refreshToken.success", True)

    # -- forgot password flow --

    def test_send_otp_forgot_password(self):
        self.stdout.write("\n--- Forgot Password Flow ---")
        data = self._gql(
            """
            mutation($input: SendOtpInput!) {
                sendOtp(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": EMAIL,
                    "purpose": "forgot_password",
                    "channel": "email",
                }
            },
        )
        self._check("sendOtp (forgot_password)", data, "data.sendOtp.success", True)

    def test_verify_otp_forgot_password(self):
        otp = self._read_otp(EMAIL, "forgot_password")
        data = self._gql(
            """
            mutation($input: VerifyOtpInput!) {
                verifyOtp(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": EMAIL,
                    "purpose": "forgot_password",
                    "code": otp,
                }
            },
        )
        self._check(
            "verifyOtp (forgot_password)", data, "data.verifyOtp.success", True
        )

    def test_forgot_password(self):
        data = self._gql(
            """
            mutation($input: ForgotPasswordInput!) {
                forgotPassword(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": EMAIL,
                    "code": "000000",
                    "newPassword1": PASSWORD,
                    "newPassword2": PASSWORD,
                }
            },
        )
        self._check("forgotPassword", data, "data.forgotPassword.success", True)

    # -- login with reset password --

    def test_login_new_password(self):
        self.stdout.write("\n--- Login After Password Reset ---")
        data = self._gql(
            """
            mutation($input: LoginInput!) {
                login(input: $input) { success message }
            }
            """,
            {"input": {"identifier": EMAIL, "password": PASSWORD}},
        )
        self._check("login (after reset)", data, "data.login.success", True)

    # -- error cases --

    def test_login_wrong_password(self):
        self.stdout.write("\n--- Error Cases ---")
        data = self._gql(
            """
            mutation($input: LoginInput!) {
                login(input: $input) { success message }
            }
            """,
            {"input": {"identifier": EMAIL, "password": "wrongpassword"}},
        )
        self._check("login (wrong password)", data, "data.login.success", False)

    def test_me_unauthenticated(self):
        data = self._gql("query { me { id } }")
        # Should return an error (no auth)
        has_errors = "errors" in data
        if has_errors:
            self.stdout.write(self.style.SUCCESS("  PASS  me (unauthenticated) -> error"))
            self.passed += 1
        else:
            self.stdout.write(self.style.ERROR("  FAIL  me (unauthenticated) -> expected error"))
            self.failed += 1

    def test_register_duplicate(self):
        # Force OTP verified state so register can proceed to uniqueness check
        cache.set(f"authkit:otp_verified:register:{EMAIL}", True, 300)
        data = self._gql(
            """
            mutation($input: RegisterInput!) {
                register(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": EMAIL,
                    "channel": "email",
                    "code": "000000",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                }
            },
        )
        self._check(
            "register (duplicate email)", data, "data.register.success", False
        )

    def test_send_otp_cooldown(self):
        # Set cooldown in settings to test rate limiting
        from django_auth_kit import settings as kit_settings
        from django.conf import settings

        original = settings.AUTH_KIT.get("OTP_COOLDOWN", 0)
        settings.AUTH_KIT["OTP_COOLDOWN"] = 60

        # Send first OTP
        self._gql(
            """
            mutation($input: SendOtpInput!) {
                sendOtp(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": "cooldown@example.com",
                    "purpose": "register",
                    "channel": "email",
                }
            },
        )
        # Second should be rate-limited
        data = self._gql(
            """
            mutation($input: SendOtpInput!) {
                sendOtp(input: $input) { success message }
            }
            """,
            {
                "input": {
                    "identifier": "cooldown@example.com",
                    "purpose": "register",
                    "channel": "email",
                }
            },
        )
        self._check("sendOtp (cooldown)", data, "data.sendOtp.success", False)

        # Restore
        settings.AUTH_KIT["OTP_COOLDOWN"] = original
