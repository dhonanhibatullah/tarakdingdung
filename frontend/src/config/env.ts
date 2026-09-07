function envString(key: string, fallback: string): string {
  const value = process.env[key];
  return value && value.trim() !== "" ? value : fallback;
}

/** Base URL of the tarakdingdung backend API. Server-side only. */
export const API_BASE_URL: string = envString(
  "TRDD_FE_API_BASE_URL",
  "http://127.0.0.1:8888",
);

/** Send the session cookie only over HTTPS. */
export const COOKIE_SECURE: boolean =
  process.env.TRDD_FE_COOKIE_SECURE === "true";

export const IS_PRODUCTION: boolean = process.env.NODE_ENV === "production";
