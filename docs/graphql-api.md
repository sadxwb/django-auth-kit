# GraphQL API Reference

The GraphQL endpoint is served at the path where you mount the URLs (e.g. `/auth/graphql/`). All requests use `POST` with a JSON body containing `query` and optional `variables`.

Authenticated mutations/queries require the `Authorization: Bearer <access_token>` header.

## Queries

### `me`

Returns the authenticated user's profile.

**Auth required:** Yes

```graphql
query {
  me {
    id
    username
    firstName
    lastName
    displayName
    avatar
    emails {
      id
      email
      isVerified
      isPrimary
    }
    mobiles {
      id
      mobile
      isVerified
      isPrimary
    }
  }
}
```

## Mutations

### `sendOtp`

Send a one-time password to an email address or mobile number.

```graphql
mutation {
  sendOtp(input: {
    identifier: "user@example.com"
    purpose: "register"       # or "forgot_password"
    channel: "email"          # or "sms"
  }) {
    success
    message
  }
}
```

### `verifyOtp`

Verify a previously sent OTP code.

```graphql
mutation {
  verifyOtp(input: {
    identifier: "user@example.com"
    purpose: "register"
    code: "123456"
  }) {
    success
    message
  }
}
```

### `register`

Create a new user account. Requires a previously verified OTP.

**Flow:** `sendOtp` -> `verifyOtp` -> `register`

```graphql
mutation {
  register(input: {
    identifier: "user@example.com"
    channel: "email"
    code: "123456"
    password1: "securepassword"
    password2: "securepassword"
    username: "johndoe"          # optional, defaults to identifier
    firstName: "John"            # optional
    lastName: "Doe"              # optional
  }) {
    success
    message
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
```

### `login`

Authenticate with an email/mobile and password. The identifier must match a primary email or mobile.

```graphql
mutation {
  login(input: {
    identifier: "user@example.com"
    password: "securepassword"
  }) {
    success
    message
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

### `refreshToken`

Exchange a valid refresh token for a new access/refresh token pair.

```graphql
mutation {
  refreshToken(input: {
    refreshToken: "eyJ..."
  }) {
    success
    message
    tokens {
      accessToken
      refreshToken
    }
  }
}
```

### `changePassword`

Change the authenticated user's password.

**Auth required:** Yes

```graphql
mutation {
  changePassword(input: {
    oldPassword: "currentpassword"
    newPassword1: "newsecurepassword"
    newPassword2: "newsecurepassword"
  }) {
    success
    message
  }
}
```

### `forgotPassword`

Reset a password using a verified OTP. Silently succeeds even if the account doesn't exist (to prevent user enumeration).

**Flow:** `sendOtp(purpose: "forgot_password")` -> `verifyOtp` -> `forgotPassword`

```graphql
mutation {
  forgotPassword(input: {
    identifier: "user@example.com"
    code: "123456"
    newPassword1: "newsecurepassword"
    newPassword2: "newsecurepassword"
  }) {
    success
    message
  }
}
```

### `updateProfile`

Update the authenticated user's profile. Supports file upload for avatar.

**Auth required:** Yes

```graphql
mutation {
  updateProfile(input: {
    firstName: "Jane"
    lastName: "Doe"
    displayName: "Jane D."
  }) {
    success
    message
    user {
      id
      displayName
      firstName
      lastName
    }
  }
}
```

For avatar uploads, use a multipart form request per the [GraphQL Multipart Request Spec](https://github.com/jaydenseric/graphql-multipart-request-spec).

### `socialLogin`

Authenticate using an access token from a social provider.

**Requires:** `django-auth-kit[social]` and provider configured in `AUTH_KIT["SOCIAL_PROVIDERS"]`.

```graphql
mutation {
  socialLogin(input: {
    provider: "google"
    accessToken: "ya29.a0..."
  }) {
    success
    message
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
```

## Response Types

### `AuthResponse`

```graphql
type AuthResponse {
  success: Boolean!
  message: String!
  tokens: AuthTokens
  user: UserType
}
```

### `AuthTokens`

```graphql
type AuthTokens {
  accessToken: String!
  refreshToken: String!
}
```

### `OperationResult`

```graphql
type OperationResult {
  success: Boolean!
  message: String!
}
```
