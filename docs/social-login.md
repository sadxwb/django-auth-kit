# Social Login

Django Auth Kit supports social authentication via [django-allauth](https://docs.allauth.org/). The client obtains an access token from the social provider (e.g. via OAuth on the frontend), then exchanges it for JWT tokens via the `socialLogin` mutation.

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
    "allauth.socialaccount.providers.microsoft",

    "django_auth_kit",
]

SITE_ID = 1
```

### 3. Enable providers in `AUTH_KIT`

```python
AUTH_KIT = {
    "SOCIAL_PROVIDERS": ["google", "facebook", "apple", "microsoft"],
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

| Provider | `provider` value | User info endpoint |
|----------|------------------|--------------------|
| Google | `"google"` | `googleapis.com/oauth2/v3/userinfo` |
| Facebook | `"facebook"` | `graph.facebook.com/me` |
| Apple | `"apple"` | Token-based (ID token) |
| Microsoft | `"microsoft"` | `graph.microsoft.com/v1.0/me` |
| Azure AD | `"azure"` | `graph.microsoft.com/v1.0/me` |

## Flow

1. **Client** authenticates with the social provider and receives an access token.
2. **Client** calls `socialLogin` with the provider name and access token.
3. **Server** fetches user info from the provider's API using the access token.
4. **Server** creates or retrieves the user, links the social account, and returns JWT tokens.

```graphql
mutation {
  socialLogin(input: {
    provider: "google"
    accessToken: "ya29.a0AfH6SM..."
  }) {
    success
    tokens {
      accessToken
      refreshToken
    }
    user {
      id
      username
      displayName
    }
  }
}
```

## Adding a Custom Provider

To add a provider not included by default:

1. Add the allauth provider app to `INSTALLED_APPS`.
2. Add the provider key to `AUTH_KIT["SOCIAL_PROVIDERS"]`.
3. Add the user-info URL to `_fetch_provider_user()` in `django_auth_kit/schema/mutations/social.py`.
