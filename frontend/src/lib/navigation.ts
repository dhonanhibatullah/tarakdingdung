import { NAVIGATION, PUBLIC_ROUTES, type NavGroup } from "@/config/navigation";
import type { PermissionName } from "@/lib/permissions";

interface RouteEntry {
  href: string;
  protected: boolean;
  requiredAny: readonly PermissionName[];
}

function buildRouteIndex(): RouteEntry[] {
  const entries: RouteEntry[] = [];
  for (const group of NAVIGATION) {
    for (const page of group.pages) {
      entries.push({
        href: page.href,
        protected: true,
        requiredAny: page.requiredAny ?? [],
      });
    }
  }
  for (const href of PUBLIC_ROUTES) {
    entries.push({ href, protected: false, requiredAny: [] });
  }
  return entries;
}

const ROUTES = buildRouteIndex();

const matchesPrefix = (pathname: string, href: string) =>
  pathname === href || pathname.startsWith(`${href}/`);

function findRoute(pathname: string): RouteEntry | undefined {
  // Longest href wins, so "/admin/users" beats "/admin".
  return [...ROUTES]
    .sort((left, right) => right.href.length - left.href.length)
    .find((route) => matchesPrefix(pathname, route.href));
}

/** Fail closed: an unknown route is treated as protected. */
export function isProtectedRoute(pathname: string): boolean {
  const route = findRoute(pathname);
  return route ? route.protected : true;
}

export function canVisitRoute(
  pathname: string,
  permissions: ReadonlySet<string>,
): boolean {
  const route = findRoute(pathname);
  if (!route) {
    return false;
  }
  return (
    route.requiredAny.length === 0 ||
    route.requiredAny.some((permission) => permissions.has(permission))
  );
}

/** The nav groups this permission set may see, empties dropped. */
export function visibleNavigation(
  permissions: ReadonlySet<PermissionName>,
): NavGroup[] {
  return NAVIGATION.flatMap((group) => {
    const pages = group.pages.filter((page) =>
      canVisitRoute(page.href, permissions),
    );
    return pages.length === 0 ? [] : [{ label: group.label, pages }];
  });
}
