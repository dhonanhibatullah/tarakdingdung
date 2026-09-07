import "server-only";

import { cookies } from "next/headers";
import { forbidden, redirect } from "next/navigation";
import { cache } from "react";

import { ApiError } from "@/lib/api/client";
import { getProfile, getProfilePermissions } from "@/lib/api/profile";
import type { UserResponse } from "@/lib/api/users";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session/cookies";
import {
  canAccessAny,
  hasPermission,
  type PermissionName,
} from "@/lib/permissions";

const INVALID_SESSION_ROUTE = "/auth/invalid-session";

export interface SessionContext {
  user: UserResponse;
  permissions: ReadonlySet<PermissionName>;
}

function interruptSessionError(error: unknown): never {
  if (error instanceof ApiError && error.status === 401) {
    redirect(INVALID_SESSION_ROUTE);
  }
  if (error instanceof ApiError && error.status === 403) {
    forbidden();
  }
  throw error;
}

export const getSession = cache(async (): Promise<UserResponse | null> => {
  const cookieStore = await cookies();
  if (!cookieStore.get(ACCESS_TOKEN_COOKIE)?.value) {
    return null;
  }
  try {
    return await getProfile();
  } catch (error) {
    interruptSessionError(error);
  }
});

export const getSessionContext = cache(
  async (): Promise<SessionContext | null> => {
    try {
      const user = await getSession();
      if (!user) {
        return null;
      }
      const permissions = await getProfilePermissions();
      return {
        user,
        permissions: new Set(permissions.map((permission) => permission.name)),
      };
    } catch (error) {
      interruptSessionError(error);
    }
  },
);

export async function requireSessionContext(): Promise<SessionContext> {
  const session = await getSessionContext();
  if (!session) {
    redirect("/login");
  }
  return session;
}

export async function requirePermission(
  permission: PermissionName,
): Promise<SessionContext> {
  const session = await requireSessionContext();
  if (!hasPermission(session.permissions, permission)) {
    forbidden();
  }
  return session;
}

export async function requireAnyPermission(
  permissions: readonly PermissionName[],
): Promise<SessionContext> {
  const session = await requireSessionContext();
  if (!canAccessAny(session.permissions, permissions)) {
    forbidden();
  }
  return session;
}
