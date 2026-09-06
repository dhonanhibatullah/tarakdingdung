from uuid import UUID

from fastapi import APIRouter, Depends, Response

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin import permission_management as pm
from tarakdingdung.domain.usecases.admin import role_management as rm
from tarakdingdung.domain.usecases.admin import user_management as um
from tarakdingdung.presentation.http.dependencies.auth import get_actor_id
from tarakdingdung.presentation.http.dependencies.container import (
    get_permission_management, get_role_management, get_user_management,
)
from tarakdingdung.presentation.http.dependencies.permission import require
from tarakdingdung.presentation.http.schemas import request as req
from tarakdingdung.presentation.http.schemas import response as res
from tarakdingdung.presentation.http.utils.pagination import (
    PaginationParams, page_response, pagination_params,
)

router = APIRouter(prefix="/v1/admin", tags=["Admin"])

_NO_CONTENT = Response(status_code=204)


def _missing(name: str) -> DomainError:
    return DomainError(f"{name} not found", ErrorType.NOT_FOUND)


# ---- Permissions -----------------------------------------------------------

@router.get("/permissions", response_model=res.PageDataResponse[res.PermissionResponse],
            dependencies=[Depends(require("permission:get"))])
async def permission_list(page: PaginationParams = Depends(pagination_params),
                          uc: pm.PermissionManagement = Depends(get_permission_management)):
    items, total = await uc.read_by_pagination(pm.ReadPermissionsByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search))
    return res.PageDataResponse[res.PermissionResponse](
        data=res.permissions_response(items), page=page_response(page, total))


@router.post("/permissions", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("permission:add"))])
async def permission_create(body: req.PermissionPostRequest,
                            actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    new_id = await uc.create(pm.CreatePermissionRequest(
        name=body.name, description=body.description, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/permissions/by-name/{name}", response_model=res.PermissionResponse,
            dependencies=[Depends(require("permission:get"))])
async def permission_by_name(name: str,
                             uc: pm.PermissionManagement = Depends(get_permission_management)):
    found = await uc.read_by_name(pm.ReadPermissionByNameRequest(name=name))
    if found is None:
        raise _missing("permission")
    return res.permission_response(found)


@router.get("/permissions/{id}", response_model=res.PermissionResponse,
            dependencies=[Depends(require("permission:get"))])
async def permission_by_id(id: UUID,
                           uc: pm.PermissionManagement = Depends(get_permission_management)):
    found = await uc.read_by_id(pm.ReadPermissionByIdRequest(id=id))
    if found is None:
        raise _missing("permission")
    return res.permission_response(found)


@router.patch("/permissions/{id}", status_code=204,
              dependencies=[Depends(require("permission:set"))])
async def permission_update(id: UUID, body: req.PermissionPatchRequest,
                            actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    await uc.update_by_id(pm.UpdatePermissionRequest(
        id=id, name=body.name, description=body.description, updated_by=actor))
    return _NO_CONTENT


@router.delete("/permissions/{id}", status_code=204,
               dependencies=[Depends(require("permission:remove"))])
async def permission_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    await uc.delete_by_id(pm.DeletePermissionRequest(id=id, deleted_by=actor))
    return _NO_CONTENT


# ---- Roles ---------------------------------------------------------------

@router.get("/roles", response_model=res.PageDataResponse[res.RoleResponse],
            dependencies=[Depends(require("role:get"))])
async def role_list(page: PaginationParams = Depends(pagination_params),
                    uc: rm.RoleManagement = Depends(get_role_management)):
    items, total = await uc.read_by_pagination(rm.ReadRolesByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search))
    return res.PageDataResponse[res.RoleResponse](
        data=res.roles_response(items), page=page_response(page, total))


@router.post("/roles", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("role:add"))])
async def role_create(body: req.RolePostRequest, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    new_id = await uc.create(rm.CreateRoleRequest(
        name=body.name, description=body.description, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/roles/default", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_default(uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_default(rm.ReadDefaultRoleRequest())
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.get("/roles/by-name/{name}", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_by_name(name: str, uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_by_name(rm.ReadRoleByNameRequest(name=name))
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.get("/roles/{id}/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("role_permission:get"))])
async def role_permissions(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    items = await uc.read_permissions(rm.ReadRolePermissionsRequest(role_id=id))
    return res.permissions_response(items)


@router.patch("/roles/{id}/default", status_code=204,
              dependencies=[Depends(require("role:set"))])
async def role_set_default(id: UUID, actor: UUID = Depends(get_actor_id),
                           uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.set_default_role(rm.SetDefaultRoleRequest(id=id, updated_by=actor))
    return _NO_CONTENT


@router.get("/roles/{id}", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_by_id(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_by_id(rm.ReadRoleByIdRequest(id=id))
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.patch("/roles/{id}", status_code=204, dependencies=[Depends(require("role:set"))])
async def role_update(id: UUID, body: req.RolePatchRequest, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.update_by_id(rm.UpdateRoleRequest(
        id=id, name=body.name, description=body.description, updated_by=actor))
    return _NO_CONTENT


@router.delete("/roles/{id}", status_code=204, dependencies=[Depends(require("role:remove"))])
async def role_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.delete_by_id(rm.DeleteRoleRequest(id=id, deleted_by=actor))
    return _NO_CONTENT


@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=201,
             response_model=res.IdResponse,
             dependencies=[Depends(require("role_permission:add"))])
async def role_permission_assign(role_id: UUID, permission_id: UUID,
                                 actor: UUID = Depends(get_actor_id),
                                 uc: rm.RoleManagement = Depends(get_role_management)):
    new_id = await uc.assign_permission(rm.AssignRolePermissionRequest(
        role_id=role_id, permission_id=permission_id, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204,
               dependencies=[Depends(require("role_permission:remove"))])
async def role_permission_revoke(role_id: UUID, permission_id: UUID,
                                 uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.revoke_permission(rm.RevokeRolePermissionRequest(
        role_id=role_id, permission_id=permission_id))
    return _NO_CONTENT


@router.get("/role-permissions",
            response_model=res.PageDataResponse[res.RolePermissionDetailResponse],
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_list(page: PaginationParams = Depends(pagination_params),
                               role_id: UUID | None = None, permission_id: UUID | None = None,
                               uc: rm.RoleManagement = Depends(get_role_management)):
    items, total = await uc.read_role_permissions_by_pagination(
        rm.ReadRolePermissionsByPaginationRequest(
            page=page.page, limit=page.limit, role_id=role_id, permission_id=permission_id))
    return res.PageDataResponse[res.RolePermissionDetailResponse](
        data=res.role_permission_details_response(items), page=page_response(page, total))


@router.get("/role-permissions/by-pair", response_model=res.RolePermissionDetailResponse,
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_by_pair(role_id: UUID, permission_id: UUID,
                                  uc: rm.RoleManagement = Depends(get_role_management)):
    result = await uc.read_role_permission_by_role_id_and_permission_id(
        rm.ReadRolePermissionByRoleIdAndPermissionIdRequest(
            role_id=role_id, permission_id=permission_id))
    return res.role_permission_detail_response(result)


@router.get("/role-permissions/{id}", response_model=res.RolePermissionDetailResponse,
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_by_id(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    result = await uc.read_role_permission_by_id(rm.ReadRolePermissionByIdRequest(id=id))
    return res.role_permission_detail_response(result)


# ---- Users -------------------------------------------------------------

@router.get("/users", response_model=res.PageDataResponse[res.UserResponse],
            dependencies=[Depends(require("user:get"))])
async def user_list(page: PaginationParams = Depends(pagination_params),
                    role_id: UUID | None = None,
                    uc: um.UserManagement = Depends(get_user_management)):
    items, total = await uc.read_by_pagination(um.ReadUsersByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search, role_id=role_id))
    return res.PageDataResponse[res.UserResponse](
        data=res.user_list_items_response(items), page=page_response(page, total))


@router.post("/users", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("user:add"))])
async def user_create(body: req.UserPostRequest, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    new_id = await uc.create(um.CreateUserRequest(
        role_id=body.role_id, name=body.name, bio=body.bio, username=body.username,
        password=body.password, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/users/by-username/{username}", response_model=res.UserResponse,
            dependencies=[Depends(require("user:get"))])
async def user_by_username(username: str,
                           uc: um.UserManagement = Depends(get_user_management)):
    found = await uc.read_by_username(um.ReadUserByUsernameRequest(username=username))
    if found is None:
        raise _missing("user")
    return res.user_response(found)


@router.get("/users/{id}/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("user_permission:get"))])
async def user_permissions(id: UUID, uc: um.UserManagement = Depends(get_user_management)):
    items = await uc.read_permissions(um.ReadUserPermissionsRequest(user_id=id))
    return res.permissions_response(items)


@router.patch("/users/{id}/password", status_code=204,
              dependencies=[Depends(require("user_password:set"))])
async def user_password(id: UUID, body: req.UserPasswordPatchRequest,
                        actor: UUID = Depends(get_actor_id),
                        uc: um.UserManagement = Depends(get_user_management)):
    await uc.reset_password(um.ResetUserPasswordRequest(
        id=id, password=body.password, updated_by=actor))
    return _NO_CONTENT


@router.get("/users/{id}", response_model=res.UserResponse,
            dependencies=[Depends(require("user:get"))])
async def user_by_id(id: UUID, uc: um.UserManagement = Depends(get_user_management)):
    found = await uc.read_by_id(um.ReadUserByIdRequest(id=id))
    if found is None:
        raise _missing("user")
    return res.user_response(found)


@router.patch("/users/{id}", status_code=204, dependencies=[Depends(require("user:set"))])
async def user_update(id: UUID, body: req.UserPatchRequest, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    await uc.update_by_id(um.UpdateUserRequest(
        id=id, role_id=body.role_id, name=body.name, bio=body.bio, username=body.username,
        updated_by=actor))
    return _NO_CONTENT


@router.delete("/users/{id}", status_code=204, dependencies=[Depends(require("user:remove"))])
async def user_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    await uc.delete_by_id(um.DeleteUserRequest(id=id, deleted_by=actor))
    return _NO_CONTENT
