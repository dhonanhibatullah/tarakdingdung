/** Reads the `exp` claim of a JWT without verifying its signature. */
export function decodeJwtExpiry(token: string): Date | null {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  try {
    const payloadJson = Buffer.from(parts[1], "base64url").toString("utf-8");
    const payload = JSON.parse(payloadJson) as { exp?: unknown };

    if (typeof payload.exp !== "number") {
      return null;
    }

    return new Date(payload.exp * 1000);
  } catch {
    return null;
  }
}
