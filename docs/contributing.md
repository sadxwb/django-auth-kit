# Contributing

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# With social login support
pip install -e ".[dev,social]"
```

## Testing

```bash
pytest                  # Run all tests
pytest tests/ -v        # Verbose
pytest tests/ -k jwt    # Filter by keyword
pytest tests/test_jwt.py  # Single file
```

Tests use an in-memory SQLite database and `locmem` cache. Django is configured entirely in `tests/conftest.py` via `pytest_configure()` — there is no standalone Django settings module.

## Generating Migrations

There is no standalone Django settings module, so use this command after model changes:

```bash
python -c "
import django; from django.conf import settings
settings.configure(
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth', 'django_auth_kit'],
    AUTH_USER_MODEL='django_auth_kit.User', DEFAULT_AUTO_FIELD='django.db.models.BigAutoField', SECRET_KEY='x')
django.setup()
from django.core.management import call_command
call_command('makemigrations', 'django_auth_kit')
"
```

## Common Tasks

- **Add a new mutation**: Create it in `schema/mutations/`, add the class to the `Mutation` base classes in `schema/schema.py`.
- **Add a new setting**: Add a function in `settings.py`, use it as `kit_settings.MY_SETTING()`.
- **Add a new SMS backend**: Subclass `BaseSmsBackend` in `otp/backends/`, implement `send_messages()`. See [SMS Backends](sms-backends.md).
- **Add a new social provider**: Add the provider string to `SOCIAL_PROVIDERS` and add its user-info URL to `_fetch_provider_user()` in `schema/mutations/social.py`. See [Social Login](social-login.md).
