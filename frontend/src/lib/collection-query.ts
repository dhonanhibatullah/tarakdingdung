import type { PageQuery, PageResponse } from "./api/types";
import {
  buildOutOfRangeRedirect,
  firstQueryValue,
  parsePositiveSafeInteger,
  type RawSearchParams,
} from "./query";

const ALLOWED_LIMITS = [12, 24, 48] as const;
const DEFAULT_LIMIT = 12;

export function parsePageQuery(
  raw: RawSearchParams,
): Required<Pick<PageQuery, "page" | "limit">> & Pick<PageQuery, "search"> {
  const page = parsePositiveSafeInteger(firstQueryValue(raw.page), 1);
  const candidate = parsePositiveSafeInteger(firstQueryValue(raw.limit), 0);
  const limit = ALLOWED_LIMITS.includes(
    candidate as (typeof ALLOWED_LIMITS)[number],
  )
    ? candidate
    : DEFAULT_LIMIT;
  const search = firstQueryValue(raw.search)?.trim() || undefined;
  return { page, limit, search };
}

/** A redirect URL when the requested page is past the last one, else undefined. */
export function getOutOfRangePageRedirect(
  pathname: string,
  raw: RawSearchParams,
  page: PageResponse,
): string | undefined {
  const requestedPage = parsePositiveSafeInteger(firstQueryValue(raw.page), 1);
  const limit = parsePositiveSafeInteger(page.limit, 0);
  const totalItems =
    Number.isSafeInteger(page.total_items) && page.total_items >= 0
      ? page.total_items
      : undefined;

  if (!limit || totalItems === undefined || totalItems === 0) {
    return undefined;
  }
  const totalPages = Math.max(1, Math.ceil(totalItems / limit));
  if (requestedPage <= totalPages) {
    return undefined;
  }
  return buildOutOfRangeRedirect(pathname, raw, totalPages);
}
