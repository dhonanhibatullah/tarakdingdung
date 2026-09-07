import "server-only";

import { cookies } from "next/headers";

import { API_BASE_URL } from "@/config/env";
import type { ErrorResponse } from "@/lib/api/types";
import { ACCESS_TOKEN_COOKIE } from "@/lib/session/cookies";

// Server-only: this whole module (and everything under src/lib/api/) never runs
// in the browser, so the backend address stays a plain env var — not
// NEXT_PUBLIC_.
const API_VERSION_PATH = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly title: string;

  constructor(status: number, title: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.title = title;
  }
}

function getBaseUrl(): string {
  return `${API_BASE_URL.replace(/\/$/, "")}${API_VERSION_PATH}`;
}

/** Builds a query string from a plain object, dropping undefined/null/"". */
export function buildQuery<T extends object>(params: T): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params) as [string, unknown][]) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export interface ApiFetchOptions {
  method?: "GET" | "HEAD" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Skip the Authorization header — only auth.ts's login/refresh need this. */
  skipAuth?: boolean;
  cache?: RequestCache;
}

async function authHeader(
  skipAuth: boolean | undefined,
): Promise<Record<string, string>> {
  if (skipAuth) {
    return {};
  }
  const cookieStore = await cookies();
  const token = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRequest(
  path: string,
  options: ApiFetchOptions = {},
): Promise<Response> {
  const { method = "GET", body, skipAuth, cache } = options;

  const headers: Record<string, string> = { ...(await authHeader(skipAuth)) };
  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  return fetch(`${getBaseUrl()}${path}`, {
    method,
    headers,
    body: requestBody,
    cache: cache ?? "no-store",
  });
}

/**
 * JSON in / JSON out. Throws ApiError on any non-2xx; returns undefined for a
 * 204. The backend's error body is `{ error, message }` (ErrorResponse).
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const response = await apiRequest(path, options);

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const errorBody = (await response
      .json()
      .catch(() => null)) as ErrorResponse | null;

    throw new ApiError(
      response.status,
      errorBody?.error ?? "Something went wrong",
      errorBody?.message ?? response.statusText,
    );
  }

  return (await response.json()) as T;
}
