import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type { PermissionResponse } from "@/lib/api/permissions";
import type {
  AuditFields,
  IdResponse,
  PageDataResponse,
  PageQuery,
} from "@/lib/api/types";

export interface RoleResponse extends AuditFields {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  preferences: Record<string, unknown>;
}

export interface WriteRoleRequest {
  name: string;
  description?: string;
}

export async function listRoles(
  query: PageQuery = {},
): Promise<PageDataResponse<RoleResponse>> {
  return apiFetch(`/admin/roles${buildQuery(query)}`);
}

export async function getRolePermissions(
  id: string,
): Promise<PermissionResponse[]> {
  return apiFetch(`/admin/roles/${id}/permissions`);
}

export async function createRole(
  request: WriteRoleRequest,
): Promise<IdResponse> {
  return apiFetch("/admin/roles", { method: "POST", body: request });
}

export async function updateRole(
  id: string,
  request: WriteRoleRequest,
): Promise<void> {
  return apiFetch(`/admin/roles/${id}`, { method: "PATCH", body: request });
}

export async function setDefaultRole(id: string): Promise<void> {
  return apiFetch(`/admin/roles/${id}/default`, { method: "PATCH", body: {} });
}

export async function deleteRole(id: string): Promise<void> {
  return apiFetch(`/admin/roles/${id}`, { method: "DELETE" });
}

export async function assignRolePermission(
  roleId: string,
  permissionId: string,
): Promise<IdResponse> {
  return apiFetch(`/admin/roles/${roleId}/permissions/${permissionId}`, {
    method: "POST",
    body: {},
  });
}

export async function revokeRolePermission(
  roleId: string,
  permissionId: string,
): Promise<void> {
  return apiFetch(`/admin/roles/${roleId}/permissions/${permissionId}`, {
    method: "DELETE",
  });
}
