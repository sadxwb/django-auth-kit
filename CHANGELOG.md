# CHANGELOG


## v0.5.2 (2026-04-18)

### Refactoring

- Update UUID generation to use uuid4 for user identifiers and enhance invitation flow with new
  email templates ([#12](https://github.com/sadxwb/django-auth-kit/pull/12),
  [`aa5dd87`](https://github.com/sadxwb/django-auth-kit/commit/aa5dd8716cccb86efdab2532de3d03f59431e9f5))

Co-authored-by: wenbinxiang <wenbin.xiang@meditsoltions.com.au>


## v0.5.1 (2026-04-09)

### Bug Fixes

- Refactor refresh token logic with async user lookup and improved error handling
  ([`08831b2`](https://github.com/sadxwb/django-auth-kit/commit/08831b2e263792daac8692def0ace236a7e5cfa2))

Adopt asynchronous methods for user retrieval using `afirst`, validate token type explicitly, and
  enhance debugging with logging for token refresh failures.


## v0.5.0 (2026-04-03)

### Features

- Add purpose and uniques check
  ([`1289cfe`](https://github.com/sadxwb/django-auth-kit/commit/1289cfe775aaf57876216fa5f7eb52caa6e77e88))


## v0.4.4 (2026-04-02)

### Refactoring

- Dynamically construct profile schema based on configurable fields
  ([`0f9163c`](https://github.com/sadxwb/django-auth-kit/commit/0f9163c34bbd18797136426b4427f70b14202d3f))

Introduce mechanisms to dynamically generate GraphQL types and input fields for user profiles based
  on configurable `EXTRA_USER_PROFILE_FIELDS`. Refactor the `updateProfile` mutation to support file
  uploads and additional fields. Update documentation to reflect these changes and clarify field
  configuration options.

- Simplify OTP logic and adopt async Django methods
  ([`ff64cc4`](https://github.com/sadxwb/django-auth-kit/commit/ff64cc4508a446ffcaae95f2bbb0d325b76f456a))

Streamline OTP management by eliminating the "purpose" parameter, deducing delivery channels
  directly from identifiers, and standardizing cache key formats. Refactor GraphQL mutations and
  services to use Django async methods (`asave`, `afirst`, etc.) for improved performance in async
  environments. Update tests and remove redundant fields from request payloads.


## v0.4.3 (2026-04-01)

### Bug Fixes

- Include package data for Django templates in setuptools configuration
  ([`3ab7d10`](https://github.com/sadxwb/django-auth-kit/commit/3ab7d10020d71b56c9cb200d1da0a0736999a322))


## v0.4.2 (2026-04-01)

### Continuous Integration

- Include `refactor` in patch tags for semantic release configuration
  ([`113e586`](https://github.com/sadxwb/django-auth-kit/commit/113e586a25fe68df5a246a8c7ce0789e2cba585f))

### Refactoring

- Replace `EmailMultiAlternatives` with `send_mail` for OTP emails
  ([`d4028d5`](https://github.com/sadxwb/django-auth-kit/commit/d4028d5d3081528c3cfbcdb31211d03473326993))

Simplify email-sending logic in the OTP service by switching from `EmailMultiAlternatives` to
  Django's `send_mail`. Update documentation to reflect the change, emphasizing compatibility with
  Django's `EMAIL_BACKEND` setting.


## v0.4.1 (2026-04-01)

### Bug Fixes

- Replace direct `info.context.request` access with `get_request` util
  ([`26ba693`](https://github.com/sadxwb/django-auth-kit/commit/26ba6935b431352a605d176b72c0a75b1a6a863e))

Simplify request access logic in GraphQL mutations by replacing direct calls to
  `info.context.request` with the reusable utility function `get_request`. Ensure consistency and
  improve maintainability across WSGI and ASGI environments.

### Continuous Integration

- Update Read the Docs config to use Python 3.13 and improve formatting
  ([`ca82d09`](https://github.com/sadxwb/django-auth-kit/commit/ca82d0951c83057cc6f3d8758bd882a47b9f9cf5))


## v0.4.0 (2026-04-01)

### Features

- Add documentation site with MkDocs and support for Read the Docs
  ([`fb24ffd`](https://github.com/sadxwb/django-auth-kit/commit/fb24ffdc525cfc4425aeb7c0e9ee9c4f7dc5cbfb))

Introduce a documentation site using MkDocs with the Material theme. Add configuration files
  (`mkdocs.yml`, `.readthedocs.yaml`) and initial documentation pages (e.g., `getting-started.md`,
  `index.md`). Include installation requirements and setup guides, covering WSGI, ASGI, and Django
  Channels configurations. Update pip dependencies and lockfile to include MkDocs support.


## v0.3.0 (2026-04-01)

### Features

- Add rate limiting to GraphQL mutations
  ([`704d104`](https://github.com/sadxwb/django-auth-kit/commit/704d104b1e8ecad97bfad18af7af6ba06e1f7ebc))

Introduce per-IP rate limiting for key GraphQL mutations (OTP, login, register, etc.) using a
  DRF-style rate format (e.g., "5/min"). Implement cache-based sliding window tracking and integrate
  with Django cache framework to allow extensible configuration via `AUTH_KIT["RATE_LIMITS"]`. Add
  tests, update documentation, and ensure compatibility with both WSGI and ASGI setups.


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
