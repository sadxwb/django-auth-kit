# CHANGELOG


## v0.2.0 (2026-03-31)

### Features

- Add `SocialLoginService` to simplify and streamline GraphQL social login integration with
  django-allauth
  ([`c441c98`](https://github.com/sadxwb/django-auth-kit/commit/c441c98fe4f310986f22dddf9eef87aa2fba2c6a))

Refactor `socialLogin` mutation to delegate token verification, user account creation, and linking
  logic to the new `SocialLoginService`. Remove provider-specific code for better maintainability
  and support for additional allauth providers with `supports_token_authentication=True`. Update
  documentation to reflect the streamlined implementation.

- Add WebSocket support for GraphQL subscriptions with JWT authentication
  ([`42367e6`](https://github.com/sadxwb/django-auth-kit/commit/42367e6e3492f04813bd5dd2bcbf0bf17c0fd20a))

Introduce `GraphQLWSConsumer` for handling WebSocket connections with JWT auth for GraphQL
  subscriptions. Update documentation, examples, and ASGI application setup. Log JWT authentication
  failures and extend dependencies to include Daphne.


## v0.1.0 (2026-03-29)

### Continuous Integration

- Add semantic release workflow and configuration
  ([`a563c73`](https://github.com/sadxwb/django-auth-kit/commit/a563c7379f84910b0f2227d89986869ab4c1324a))

- Remove build command from semantic release configuration
  ([`85ce5ef`](https://github.com/sadxwb/django-auth-kit/commit/85ce5efa56ec6b468d9fa246dfb0908cb8b4a25e))

### Features

- Init
  ([`c96c50b`](https://github.com/sadxwb/django-auth-kit/commit/c96c50bd164e047e5189bdb4815b6a482b856031))

- Refactor schema definitions: use `merge_types` for `Query` and `Mutation`, standardize type names
  ([`938cac1`](https://github.com/sadxwb/django-auth-kit/commit/938cac1bfa88a893035758cda6a8aeb88056cb29))
