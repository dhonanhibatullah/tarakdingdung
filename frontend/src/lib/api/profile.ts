import "server-only";

import { apiFetch } from "@/lib/api/client";
import type { PermissionResponse } from "@/lib/api/permissions";
import type { UserResponse } from "@/lib/api/users";

/** The currently authenticated user, resolved from the access token. */
export async function getProfile(): Promise<UserResponse> {
  return apiFetch("/profile");
}

export async function getProfilePermissions(): Promise<PermissionResponse[]> {
  return apiFetch("/profile/permissions");
}
