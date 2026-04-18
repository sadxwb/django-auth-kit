# Social Login

Django Auth Kit supports social authentication via [django-allauth](https://docs.allauth.org/). The client obtains a token from the social provider (e.g. via OAuth on the frontend), then exchanges it for JWT tokens via the `socialLogin` mutation.

All provider-specific logic (token verification, user-info extraction, account linking) is handled by allauth's provider infrastructure. Any provider that allauth supports with `supports_token_authentication = True` works automatically.

## Setup

### 1. Install the social extra

```bash
pip install django-auth-kit[social]
```

### 2. Add allauth to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    # Add the providers you need:
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.openid_connect",

    "django_auth_kit",
]

SITE_ID = 1
```

### 3. Enable providers in `AUTH_KIT`

```python
AUTH_KIT = {
    "SOCIAL_PROVIDERS": ["google", "facebook", "apple"],
}
```

### 4. Configure provider credentials

Add `SocialApp` entries via the Django admin, or configure in settings:

```python
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "offline"},
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
        "FIELDS": ["id", "name", "email", "first_name", "last_name", "picture"],
    },
}
```

### 5. Run allauth migrations

```bash
python manage.py migrate
```

## Supported Providers

Any allauth provider with `supports_token_authentication = True` works. As of allauth v65:

| Provider | `provider` value | Token type |
|----------|------------------|------------|
| Google | `"google"` | `id_token` |
| Facebook | `"facebook"` | `access_token` |
| Apple | `"apple"` | `id_token` |
| OpenID Connect | `"openid_connect"` | `id_token` |

Providers that only support redirect-based OAuth (e.g. Microsoft, GitHub) use the **redirect flow** described below.

## Flow

1. **Client** authenticates with the social provider and receives a token.
2. **Client** calls `socialLogin` with the provider name and token.
3. **Server** delegates to allauth's `provider.verify_token()` which validates the token and extracts user info using the provider's own logic.
4. **Server** uses allauth's `sociallogin.lookup()` to match against existing accounts (by social account UID or verified email).
5. **Server** creates or retrieves the user (via allauth's adapter hooks) and returns JWT tokens.

```graphql
# Google (uses id_token)
mutation {
  socialLogin(input: {
    provider: "google"
    idToken: "eyJhbGciOiJSUzI1NiIs..."
  }) {
    success
    tokens {
      accessToken
      refreshToken
    }
    user {
      id
      username
    }
  }
}

# Facebook (uses access_token)
mutation {
  socialLogin(input: {
    provider: "facebook"
    accessToken: "EAAGm0PX4ZCps..."
  }) {
    success
    tokens {
      accessToken
      refreshToken
    }
  }
}
```

## How It Works

The `SocialLoginService` in `django_auth_kit/social/service.py` bridges the GraphQL mutation to allauth:

1. **Provider resolution**: Uses `allauth.socialaccount.adapter.get_adapter().get_provider()` to resolve the provider class, including `SocialApp` configuration.

2. **Token verification**: Calls `provider.verify_token(request, token)` — each allauth provider implements this differently:
   - **Google**: Decodes and verifies the ID token JWT against Google's public keys.
   - **Apple**: Decodes the ID token against Apple's JWKS endpoint.
   - **Facebook**: Exchanges the access token for user info via Facebook's Graph API.
   - **OpenID Connect**: Verifies the ID token against the provider's JWKS.

3. **Account matching**: `sociallogin.lookup()` checks for existing `SocialAccount` by provider + UID, then falls back to matching by verified email.

4. **User creation**: For new users, `adapter.save_user()` creates the user, respecting allauth's adapter hooks (`populate_user`, `is_open_for_signup`, etc.).

5. **JWT issuance**: After allauth resolves the user, django-auth-kit issues its own JWT token pair.

## Customization

Since all user creation flows through allauth's adapter, you can customize behavior by subclassing `DefaultSocialAccountAdapter`:

```python
# myapp/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Custom logic here
        return user

    def is_open_for_signup(self, request, sociallogin):
        # Control who can sign up
        return True
```

```python
# settings.py
SOCIALACCOUNT_ADAPTER = "myapp.adapters.MySocialAccountAdapter"
```

## Redirect-Based OAuth (Microsoft, GitHub, etc.)

For providers that use OAuth2 authorization-code flow (redirect-based), django-auth-kit provides built-in views that handle the entire flow and issue JWT tokens at the end.

### Setup (Microsoft / Azure AD example)

#### 1. Add the provider to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "allauth.socialaccount.providers.microsoft",
    "django_auth_kit",
]
```

#### 2. Configure the provider

```python
AUTH_KIT = {
    "SOCIAL_PROVIDERS": ["microsoft"],
    "SOCIAL_LOGIN_REDIRECT_URL": "https://your-frontend.com/auth/callback",
}

SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "SCOPE": ["User.Read", "email", "openid", "profile"],
        "AUTH_PARAMS": {
            "prompt": "select_account",
        },
    },
}
```

#### 3. Add a `SocialApp` with your Azure AD app credentials

Via Django admin or in settings. The `client_id` and `secret` come from your
Azure AD app registration (registered once by the developer, not per-org).

#### 4. Include the URLs

```python
urlpatterns = [
    path("auth/", include("django_auth_kit.urls")),
]
```

### Redirect Flow

1. **Frontend** queries `socialLoginUrl(provider: "microsoft")` to get the redirect URL.
2. **Frontend** redirects the user to that URL.
3. **User** authenticates on the provider's login page.
4. **Provider** redirects back to `/auth/social/microsoft/callback/`.
5. **Server** exchanges the code for tokens, creates/links the user via allauth, and issues JWT tokens.
6. **Server** redirects to `SOCIAL_LOGIN_REDIRECT_URL` with `access_token` and `refresh_token` as query parameters.

```graphql
query {
  socialLoginUrl(provider: "microsoft", nextUrl: "https://app.example.com/auth/callback") {
    url
    provider
  }
}
```

Or link directly to `/auth/social/microsoft/login/?next=https://app.example.com/auth/callback`.

### Admin Consent (Azure AD Multi-Tenant)

For multi-tenant Azure AD apps where an org admin must grant consent:

```python
SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "SCOPE": ["User.Read", "email", "openid", "profile"],
        "AUTH_PARAMS": {
            "prompt": "admin_consent",  # forces admin consent screen
        },
    },
}
```

After the admin grants consent, users from that Azure AD tenant can log in via the standard login flow (without `admin_consent` prompt).

## Adding a New Provider

To add any allauth provider:

**Token-based** (Google, Apple, Facebook): Add the provider app to `INSTALLED_APPS`, add to `AUTH_KIT["SOCIAL_PROVIDERS"]`, configure credentials. Use the `socialLogin` mutation.

**Redirect-based** (Microsoft, GitHub): Same setup, plus set `SOCIAL_LOGIN_REDIRECT_URL`. Use the `socialLoginUrl` query or link to `/auth/social/<provider>/login/`.
