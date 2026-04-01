# Django Auth Kit

A batteries-included Django authentication package with Strawberry GraphQL, JWT tokens, OTP verification, and optional social login via django-allauth.

## Features

- **UserEmail & UserMobile models** with `is_verified` / `is_primary` support (bring your own User model)
- **OTP verification** via email (Django email backend) and SMS (pluggable backend)
- **JWT authentication** with access + refresh token pairs
- **Strawberry GraphQL API** for all auth operations
- **Social login** via django-allauth (Google, Facebook, Apple, OpenID Connect)
- **Rate limiting** per client IP with DRF-style configurable rates
- **WSGI & ASGI** support, including Django Channels consumers
- **Fully configurable** via a single `AUTH_KIT` dict in Django settings

## Quick Links

- [Installation & Quick Start](getting-started.md)
- [Configuration Reference](configuration.md)
- [GraphQL API Reference](graphql-api.md)
- [Architecture & Design](architecture.md)

## GraphQL Mutations

| Mutation | Auth Required | Description |
|----------|---------------|-------------|
| `sendOtp` | No | Send an OTP code to an email or mobile |
| `verifyOtp` | No | Verify an OTP code |
| `register` | No | Register with verified OTP + password |
| `login` | No | Login with email/mobile + password |
| `refreshToken` | No | Get a new token pair from a refresh token |
| `changePassword` | Yes | Change password (requires current password) |
| `forgotPassword` | No | Reset password with verified OTP |
| `updateProfile` | Yes | Update first/last name |
| `socialLogin` | No | Authenticate via a social provider |
