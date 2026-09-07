import "server-only";

import { cookies } from "next/headers";

import { COOKIE_SECURE } from "@/config/env";
import { apiFetch } from "@/lib/api/client";
import type { PermissionResponse } from "@/lib/api/permissions";
import type { RoleResponse } from "@/lib/api/roles";
import type { UserResponse } from "@/lib/api/users";
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
} from "@/lib/session/cookies";
import { decodeJwtExpiry } from "@/lib/session/jwt";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: UserResponse;
  role: RoleResponse;
  permissions: PermissionResponse[];
  access_token: string;
  refresh_token: string;
}

async function persistSession(session: LoginResponse): Promise<void> {
  const cookieStore = await cookies();

  // Each cookie's expiry mirrors its own JWT's `exp`, so it stays correct
  // whatever TRDD_BE_TOKEN_*_TTL_SECONDS is set to. Falls back to a session
  // cookie only if the token is unparsable.
  const accessExpires = decodeJwtExpiry(session.access_token) ?? undefined;
  const refreshExpires = decodeJwtExpiry(session.refresh_token) ?? undefined;
  const base = {
    httpOnly: true,
    secure: COOKIE_SECURE,
    sameSite: "lax",
    path: "/",
  } as const;

  cookieStore.set(ACCESS_TOKEN_COOKIE, session.access_token, {
    ...base,
    expires: accessExpires,
  });
  cookieStore.set(REFRESH_TOKEN_COOKIE, session.refresh_token, {
    ...base,
    expires: refreshExpires,
  });
}

/** Logs in and sets the httpOnly access/refresh cookies. No token yet, so no
 *  Authorization header. */
export async function login(request: LoginRequest): Promise<LoginResponse> {
  const session = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: request,
    skipAuth: true,
  });
  await persistSession(session);
  return session;
}

/** Exchanges the refresh-token cookie for a fresh pair and re-persists both. */
export async function refresh(): Promise<LoginResponse> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;
  if (!refreshToken) {
    throw new Error("No refresh token cookie present");
  }
  const session = await apiFetch<LoginResponse>("/auth/refresh", {
    method: "POST",
    body: { refresh_token: refreshToken },
    skipAuth: true,
  });
  await persistSession(session);
  return session;
}

/** Clears the session cookies. There is no backend logout endpoint. */
export async function logout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(ACCESS_TOKEN_COOKIE);
  cookieStore.delete(REFRESH_TOKEN_COOKIE);
}
