import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type {
  AuditFields,
  IdResponse,
  PageDataResponse,
  PageQuery,
} from "@/lib/api/types";

export interface PermissionResponse extends AuditFields {
  id: string;
  name: string;
  description: string;
  preferences: Record<string, unknown>;
}

export interface WritePermissionRequest {
  name: string;
  description?: string;
}

export async function listPermissions(
  query: PageQuery = {},
): Promise<PageDataResponse<PermissionResponse>> {
  return apiFetch(`/admin/permissions${buildQuery(query)}`);
}

export async function createPermission(
  request: WritePermissionRequest,
): Promise<IdResponse> {
  return apiFetch("/admin/permissions", { method: "POST", body: request });
}

export async function updatePermission(
  id: string,
  request: WritePermissionRequest,
): Promise<void> {
  return apiFetch(`/admin/permissions/${id}`, {
    method: "PATCH",
    body: request,
  });
}

export async function deletePermission(id: string): Promise<void> {
  return apiFetch(`/admin/permissions/${id}`, { method: "DELETE" });
}
