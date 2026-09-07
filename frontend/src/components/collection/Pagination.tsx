import Link from "next/link";

import type { PageResponse } from "@/lib/api/types";
import type { RawSearchParams } from "@/lib/query";

interface PaginationProps {
  page: PageResponse;
  searchParams: RawSearchParams;
  pathname: string;
}

function pageHref(
  pathname: string,
  searchParams: RawSearchParams,
  page: number,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (value === undefined || key === "page") {
      continue;
    }
    for (const item of Array.isArray(value) ? value : [value]) {
      params.append(key, item);
    }
  }
  params.set("page", String(page));
  return `${pathname}?${params.toString()}`;
}

const CONTROL_CLASS =
  "focus-visible:ring-focus focus-visible:ring-offset-background rounded-xl px-4 py-2.5 text-sm font-semibold focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none";

function Control({
  children,
  disabled,
  href,
}: {
  children: string;
  disabled: boolean;
  href: string;
}) {
  if (disabled) {
    return (
      <span
        aria-disabled="true"
        className={`${CONTROL_CLASS} cursor-not-allowed opacity-50`}
      >
        {children}
      </span>
    );
  }
  return (
    <Link className={`text-primary hover:bg-highlight/40 ${CONTROL_CLASS}`} href={href}>
      {children}
    </Link>
  );
}

export default function Pagination({
  page,
  pathname,
  searchParams,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(page.total_items / page.limit));
  const currentPage = Math.min(Math.max(1, page.page), totalPages);

  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-3"
    >
      <Control
        disabled={currentPage === 1}
        href={pageHref(pathname, searchParams, currentPage - 1)}
      >
        Previous page
      </Control>
      <p className="text-muted-foreground text-sm" aria-live="polite">
        Page {currentPage} of {totalPages}
      </p>
      <Control
        disabled={currentPage === totalPages}
        href={pageHref(pathname, searchParams, currentPage + 1)}
      >
        Next page
      </Control>
    </nav>
  );
}
