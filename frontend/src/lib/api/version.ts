import "server-only";

import { API_BASE_URL } from "@/config/env";

/**
 * Not under /api/v1 — the backend serves it as plain text at /api/version,
 * unauthenticated. Bypasses apiFetch's JSON + /api/v1 assumptions.
 */
export async function getAppVersion(): Promise<string | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL.replace(/\/$/, "")}/api/version`,
      { cache: "no-store" },
    );
    if (!response.ok) {
      return null;
    }
    return (await response.text()).trim();
  } catch {
    return null;
  }
}
