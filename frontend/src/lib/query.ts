export type RawSearchParams = Record<string, string | string[] | undefined>;

export function firstQueryValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function parsePositiveSafeInteger(
  value: unknown,
  fallback: number,
): number {
  if (
    (typeof value !== "number" && typeof value !== "string") ||
    (typeof value === "string" && !/^\d+$/.test(value))
  ) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function parseEnumQuery<const T extends readonly string[]>(
  value: unknown,
  values: T,
): T[number] | undefined {
  return typeof value === "string" && values.includes(value)
    ? (value as T[number])
    : undefined;
}

/** Rebuilds `?…` from a raw params map, replacing `page` with `lastPage`. */
export function buildOutOfRangeRedirect(
  pathname: string,
  values: RawSearchParams,
  lastPage: number,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || key === "page") {
      continue;
    }
    for (const item of Array.isArray(value) ? value : [value]) {
      params.append(key, item);
    }
  }
  params.set("page", String(lastPage));
  return `${pathname}?${params.toString()}`;
}
