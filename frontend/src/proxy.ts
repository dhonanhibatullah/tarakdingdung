import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { API_BASE_URL, COOKIE_SECURE } from "@/config/env";
import { isProtectedRoute } from "@/lib/navigation";
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
} from "@/lib/session/cookies";
import { decodeJwtExpiry } from "@/lib/session/jwt";

const API_VERSION_PATH = "/api/v1";
const REFRESH_BUFFER_MS = 10_000;
const AUTH_ONLY_ROUTES = ["/login"];

interface RefreshedTokens {
  access_token: string;
  refresh_token: string;
}

function isExpiredOrNear(expiry: Date | null): boolean {
  if (!expiry) {
    return true;
  }
  return expiry.getTime() - Date.now() <= REFRESH_BUFFER_MS;
}

async function tryRefresh(
  refreshToken: string,
): Promise<RefreshedTokens | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL.replace(/\/$/, "")}${API_VERSION_PATH}/auth/refresh`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
    );
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as RefreshedTokens;
  } catch {
    return null;
  }
}

function setSessionCookies(
  response: NextResponse,
  tokens: RefreshedTokens,
): void {
  const base = {
    httpOnly: true,
    secure: COOKIE_SECURE,
    sameSite: "lax",
    path: "/",
  } as const;
  response.cookies.set(ACCESS_TOKEN_COOKIE, tokens.access_token, {
    ...base,
    expires: decodeJwtExpiry(tokens.access_token) ?? undefined,
  });
  response.cookies.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, {
    ...base,
    expires: decodeJwtExpiry(tokens.refresh_token) ?? undefined,
  });
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  let accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  let refreshedTokens: RefreshedTokens | null = null;
  if (
    refreshToken &&
    isExpiredOrNear(accessToken ? decodeJwtExpiry(accessToken) : null)
  ) {
    refreshedTokens = await tryRefresh(refreshToken);
    accessToken = refreshedTokens?.access_token;
  }

  const hasSession = Boolean(
    accessToken && !isExpiredOrNear(decodeJwtExpiry(accessToken)),
  );

  let response: NextResponse;
  if (isProtectedRoute(pathname) && !hasSession) {
    response = NextResponse.redirect(new URL("/login", request.nextUrl));
  } else if (AUTH_ONLY_ROUTES.includes(pathname) && hasSession) {
    response = NextResponse.redirect(new URL("/dashboard", request.nextUrl));
  } else {
    if (refreshedTokens) {
      request.cookies.set(ACCESS_TOKEN_COOKIE, refreshedTokens.access_token);
      request.cookies.set(REFRESH_TOKEN_COOKIE, refreshedTokens.refresh_token);
    }
    response = NextResponse.next({ request });
  }

  if (refreshedTokens) {
    setSessionCookies(response, refreshedTokens);
  }
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
