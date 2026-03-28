# Contributing

## Development Setup

```bash
uv sync

# With all optional dependencies
uv sync --all-extras
```

## Testing

```bash
uv run pytest                  # Run all tests
uv run pytest tests/ -v        # Verbose
uv run pytest tests/ -k jwt    # Filter by keyword
uv run pytest tests/test_jwt.py  # Single file
```

### Example project

There is an example Django project in `example/` for manual testing:

```bash
cd example
uv run python manage.py migrate
uv run python manage.py runserver

# Run all endpoint tests (registration, login, password, etc.)
uv run python manage.py test_endpoints
```

Tests use an in-memory SQLite database and `locmem` cache. Django is configured entirely in `tests/conftest.py` via `pytest_configure()` — there is no standalone Django settings module.

## Generating Migrations

There is no standalone Django settings module, so use this command after model changes:

```bash
cd example
uv run python manage.py makemigrations django_auth_kit
```

## Common Tasks

- **Add a new mutation**: Create it in `schema/mutations/`, add the class to the `Mutation` base classes in `schema/schema.py`.
- **Add a new setting**: Add a function in `settings.py`, use it as `kit_settings.MY_SETTING()`.
- **Add a new SMS backend**: Subclass `BaseSmsBackend` in `otp/backends/`, implement `send_messages()`. See [SMS Backends](sms-backends.md).
- **Add a new social provider**: Add the provider string to `SOCIAL_PROVIDERS` and add its user-info URL to `_fetch_provider_user()` in `schema/mutations/social.py`. See [Social Login](social-login.md).
