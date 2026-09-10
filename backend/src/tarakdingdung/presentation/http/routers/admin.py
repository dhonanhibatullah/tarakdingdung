from fastapi import APIRouter, Depends

from tarakdingdung.domain.usecases.admin.permission_management import (
    AddPermissionRequest,
)
from tarakdingdung.domain.usecases.admin.role_management import AddRoleRequest
from tarakdingdung.domain.usecases.admin.user_management import AddUserRequest
from tarakdingdung.presentation.http.dependencies.auth import require_permission
from tarakdingdung.presentation.http.dependencies.container import get_container
from tarakdingdung.presentation.http.schemas.request import (
    AddPermissionBody,
    AddRoleBody,
    AddUserBody,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/permissions", dependencies=[Depends(require_permission("admin"))])
async def add_permission(body: AddPermissionBody, container=Depends(get_container)):
    perm = await container.permission_management.add(
        AddPermissionRequest(name=body.name, description=body.description)
    )
    return {"id": perm.id, "name": perm.name, "description": perm.description}


@router.get("/permissions", dependencies=[Depends(require_permission("admin"))])
async def list_permissions(page: int = 1, per_page: int = 20, container=Depends(get_container)):
    items, total = await container.permission_management.list(page, per_page)
    return {
        "items": [{"id": p.id, "name": p.name, "description": p.description} for p in items],
        "total": total,
    }


@router.post("/roles", dependencies=[Depends(require_permission("admin"))])
async def add_role(body: AddRoleBody, container=Depends(get_container)):
    role = await container.role_management.add(
        AddRoleRequest(
            name=body.name, description=body.description, is_default=body.is_default
        )
    )
    return {"id": role.id, "name": role.name, "description": role.description}


@router.get("/roles", dependencies=[Depends(require_permission("admin"))])
async def list_roles(page: int = 1, per_page: int = 20, container=Depends(get_container)):
    items, total = await container.role_management.list(page, per_page)
    return {
        "items": [{"id": r.id, "name": r.name, "description": r.description} for r in items],
        "total": total,
    }


@router.get("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("admin"))])
async def role_permissions(role_id: str, container=Depends(get_container)):
    perms = await container.role_management.permissions(role_id)
    return {"items": [{"id": p.id, "name": p.name} for p in perms]}


@router.post("/users", dependencies=[Depends(require_permission("admin"))])
async def add_user(body: AddUserBody, container=Depends(get_container)):
    user = await container.user_management.add(
        AddUserRequest(
            username=body.username,
            email=body.email,
            password=body.password,
            role_names=body.role_names,
        )
    )
    return {"id": user.id, "username": user.username, "email": user.email}


@router.get("/users", dependencies=[Depends(require_permission("admin"))])
async def list_users(page: int = 1, per_page: int = 20, container=Depends(get_container)):
    items, total = await container.user_management.list(page, per_page)
    return {
        "items": [
            {"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active}
            for u in items
        ],
        "total": total,
    }


@router.post("/users/{user_id}/deactivate", dependencies=[Depends(require_permission("admin"))])
async def deactivate_user(user_id: str, container=Depends(get_container)):
    user = await container.user_management.deactivate(user_id)
    return {"id": user.id, "username": user.username, "is_active": user.is_active}
