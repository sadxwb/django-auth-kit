from __future__ import annotations

import strawberry


@strawberry.type
class AuthTokens:
    access_token: str
    refresh_token: str


@strawberry.type
class OperationResult:
    success: bool
    message: str


@strawberry.type
class UserEmailType:
    id: strawberry.ID
    email: str
    is_verified: bool
    is_primary: bool


@strawberry.type
class UserMobileType:
    id: strawberry.ID
    mobile: str
    is_verified: bool
    is_primary: bool


@strawberry.type
class UserType:
    id: strawberry.ID
    username: str
    first_name: str
    last_name: str
    display_name: str
    avatar: str
    emails: list[UserEmailType]
    mobiles: list[UserMobileType]


@strawberry.type
class AuthResponse:
    success: bool
    message: str
    tokens: AuthTokens | None = None
    user: UserType | None = None
