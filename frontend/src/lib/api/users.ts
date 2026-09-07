import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type { PermissionResponse } from "@/lib/api/permissions";
import type {
  AuditFields,
  IdResponse,
  PageDataResponse,
  PageQuery,
} from "@/lib/api/types";

export interface UserResponse extends AuditFields {
  id: string;
  role_id: string;
  role_name?: string | null;
  name: string;
  bio: string;
  username: string;
  preferences: Record<string, unknown>;
}

export interface ListUsersQuery extends PageQuery {
  role_id?: string;
}

export interface CreateUserRequest {
  role_id: string;
  name: string;
  username: string;
  password: string;
  bio?: string;
}

export interface UpdateUserRequest {
  role_id?: string;
  name?: string;
  bio?: string;
  username?: string;
}

export async function listUsers(
  query: ListUsersQuery = {},
): Promise<PageDataResponse<UserResponse>> {
  return apiFetch(`/admin/users${buildQuery(query)}`);
}

export async function getUser(id: string): Promise<UserResponse> {
  return apiFetch(`/admin/users/${id}`);
}

export async function getUserPermissions(
  id: string,
): Promise<PermissionResponse[]> {
  return apiFetch(`/admin/users/${id}/permissions`);
}

export async function createUser(
  request: CreateUserRequest,
): Promise<IdResponse> {
  return apiFetch("/admin/users", { method: "POST", body: request });
}

export async function updateUser(
  id: string,
  request: UpdateUserRequest,
): Promise<void> {
  return apiFetch(`/admin/users/${id}`, { method: "PATCH", body: request });
}

export async function resetUserPassword(
  id: string,
  password: string,
): Promise<void> {
  return apiFetch(`/admin/users/${id}/password`, {
    method: "PATCH",
    body: { password },
  });
}

export async function deleteUser(id: string): Promise<void> {
  return apiFetch(`/admin/users/${id}`, { method: "DELETE" });
}
