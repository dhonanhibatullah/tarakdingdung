from dataclasses import dataclass

from fastapi import Depends, Request

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.usecases.admin.permission_management import PermissionManagement
from tarakdingdung.domain.usecases.admin.role_management import RoleManagement
from tarakdingdung.domain.usecases.admin.user_management import UserManagement
from tarakdingdung.domain.usecases.auth.session import Session
from tarakdingdung.domain.usecases.profile.account import Account
from tarakdingdung.domain.usecases.profile.me import Me
from tarakdingdung.domain.usecases.profile.security import Security


@dataclass(frozen=True, slots=True)
class Container:
    session: Session
    permission_management: PermissionManagement
    role_management: RoleManagement
    user_management: UserManagement
    profile_me: Me
    profile_account: Account
    profile_security: Security
    token: Token


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_token(container: Container = Depends(get_container)) -> Token:
    return container.token


def get_session_usecase(container: Container = Depends(get_container)) -> Session:
    return container.session


def get_permission_management(
        container: Container = Depends(get_container)) -> PermissionManagement:
    return container.permission_management


def get_role_management(container: Container = Depends(get_container)) -> RoleManagement:
    return container.role_management


def get_user_management(container: Container = Depends(get_container)) -> UserManagement:
    return container.user_management


def get_profile_me(container: Container = Depends(get_container)) -> Me:
    return container.profile_me


def get_profile_account(container: Container = Depends(get_container)) -> Account:
    return container.profile_account


def get_profile_security(container: Container = Depends(get_container)) -> Security:
    return container.profile_security
