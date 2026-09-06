from uuid import UUID

from pydantic import BaseModel


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class PermissionPostRequest(BaseModel):
    name: str
    description: str | None = None


class PermissionPatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePostRequest(BaseModel):
    name: str
    description: str | None = None


class RolePatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class UserPostRequest(BaseModel):
    role_id: UUID
    name: str
    bio: str | None = None
    username: str
    password: str


class UserPatchRequest(BaseModel):
    role_id: UUID | None = None
    name: str | None = None
    bio: str | None = None
    username: str | None = None


class UserPasswordPatchRequest(BaseModel):
    password: str


class ProfilePatchRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    username: str | None = None


class ProfilePasswordPatchRequest(BaseModel):
    current_password: str
    new_password: str
