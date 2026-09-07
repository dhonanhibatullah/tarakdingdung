export function formText(formData: FormData, name: string): string {
  const entry = formData.get(name);
  return typeof entry === "string" ? entry.trim() : "";
}

export function optionalString(
  formData: FormData,
  name: string,
): string | undefined {
  return formText(formData, name) || undefined;
}

export function formBool(formData: FormData, name: string): boolean {
  const entry = formData.get(name);
  return entry === "on" || entry === "true" || entry === "1";
}

/** Parses a textarea into a plain JSON object, or returns an error string. */
export function parseJsonObject(
  raw: string,
): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: true, value: {} };
  }
  try {
    const value: unknown = JSON.parse(trimmed);
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { ok: false, error: "Enter a JSON object." };
    }
    return { ok: true, value: value as Record<string, unknown> };
  } catch {
    return { ok: false, error: "Enter valid JSON." };
  }
}
