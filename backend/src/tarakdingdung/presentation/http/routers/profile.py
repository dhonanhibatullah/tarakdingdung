from uuid import UUID

from fastapi import APIRouter, Depends, Response

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.account import Account, UpdateProfileRequest
from tarakdingdung.domain.usecases.profile.me import (
    GetProfilePermissionsRequest, GetProfileRequest, Me,
)
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security
from tarakdingdung.presentation.http.dependencies.auth import get_actor_id
from tarakdingdung.presentation.http.dependencies.container import (
    get_profile_account, get_profile_me, get_profile_security,
)
from tarakdingdung.presentation.http.dependencies.permission import require
from tarakdingdung.presentation.http.schemas import request as req
from tarakdingdung.presentation.http.schemas import response as res

router = APIRouter(prefix="/v1/profile", tags=["Profile"])


@router.get("", response_model=res.UserResponse, dependencies=[Depends(require("profile:get"))])
async def profile_get(actor: UUID = Depends(get_actor_id),
                      uc: Me = Depends(get_profile_me)):
    user = await uc.get_profile(GetProfileRequest(user_id=actor))
    if user is None:
        raise DomainError("user not found", ErrorType.NOT_FOUND)
    return res.user_response(user)


@router.get("/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("profile:get"))])
async def profile_permissions(actor: UUID = Depends(get_actor_id),
                              uc: Me = Depends(get_profile_me)):
    items = await uc.get_permissions(GetProfilePermissionsRequest(user_id=actor))
    return res.permissions_response(items)


@router.patch("", status_code=204, dependencies=[Depends(require("profile:set"))])
async def profile_update(body: req.ProfilePatchRequest, actor: UUID = Depends(get_actor_id),
                         uc: Account = Depends(get_profile_account)):
    await uc.update_profile(UpdateProfileRequest(
        user_id=actor, name=body.name, bio=body.bio, username=body.username, updated_by=actor))
    return Response(status_code=204)


@router.patch("/password", status_code=204,
              dependencies=[Depends(require("profile_security:set"))])
async def profile_password(body: req.ProfilePasswordPatchRequest,
                           actor: UUID = Depends(get_actor_id),
                           uc: Security = Depends(get_profile_security)):
    await uc.change_password(ChangePasswordRequest(
        user_id=actor, current_password=body.current_password,
        new_password=body.new_password, updated_by=actor))
    return Response(status_code=204)
