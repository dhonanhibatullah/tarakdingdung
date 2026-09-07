import type { Metadata } from "next";
import { redirect } from "next/navigation";

import Pagination from "@/components/collection/Pagination";
import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";
import { listPermissions } from "@/lib/api/permissions";
import { listRoles } from "@/lib/api/roles";
import {
  getOutOfRangePageRedirect,
  parsePageQuery,
} from "@/lib/collection-query";
import { firstQueryValue, parseEnumQuery, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";

import NewPermissionDialog from "./_components/NewPermissionDialog";
import NewRoleDialog from "./_components/NewRoleDialog";
import PermissionCard from "./_components/PermissionCard";
import RoleCard from "./_components/RoleCard";
import Tabs from "./_components/Tabs";

export const metadata: Metadata = {
  title: "Access Control — Tarakdingdung",
  description: "Roles and the permissions they grant.",
};

interface AccessControlPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function AccessControlPage({
  searchParams,
}: AccessControlPageProps) {
  const { permissions } = await requireAnyPermission([
    "role:get",
    "permission:get",
    "role_permission:get",
  ]);
  const raw = await searchParams;
  const pageQuery = parsePageQuery(raw);

  const canSeeRoles = permissions.has("role:get");
  const canSeePermissions = permissions.has("permission:get");
  const requested = parseEnumQuery(firstQueryValue(raw.tab), [
    "roles",
    "permissions",
  ] as const);
  const active: "roles" | "permissions" =
    requested === "permissions" && canSeePermissions
      ? "permissions"
      : canSeeRoles
        ? "roles"
        : "permissions";

  // The full permission list backs the per-role checkbox matrix.
  const allPermissions = canSeePermissions
    ? await listPermissions({ limit: 200 }).then((r) =>
        r.data.map((p) => ({
          id: p.id,
          name: p.name,
          description: p.description,
        })),
      )
    : [];

  const rolesResult =
    active === "roles" && canSeeRoles
      ? await listRoles({ page: pageQuery.page, limit: pageQuery.limit, search: pageQuery.search })
      : null;
  const permissionsResult =
    active === "permissions" && canSeePermissions
      ? await listPermissions({
          page: pageQuery.page,
          limit: pageQuery.limit,
          search: pageQuery.search,
        })
      : null;

  const activeResult = rolesResult ?? permissionsResult;
  if (activeResult) {
    const outOfRange = getOutOfRangePageRedirect(
      "/admin/access-control",
      { page: raw.page, tab: active, limit: String(pageQuery.limit) },
      activeResult.page,
    );
    if (outOfRange) {
      redirect(outOfRange);
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Access Control"
        description="Roles bundle permissions; permissions gate individual endpoints. A user inherits every permission on their role."
        actions={
          active === "roles"
            ? permissions.has("role:add")
              ? <NewRoleDialog />
              : undefined
            : permissions.has("permission:add")
              ? <NewPermissionDialog />
              : undefined
        }
      />

      <Tabs active={active} showPermissions={canSeePermissions} />

      {active === "roles" && rolesResult ? (
        <>
          {rolesResult.data.length > 0 ? (
            <section
              aria-label="Roles"
              className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
            >
              {rolesResult.data.map((role) => (
                <RoleCard
                  key={role.id}
                  role={role}
                  permissions={allPermissions}
                  sessionPermissions={permissions}
                />
              ))}
            </section>
          ) : (
            <EmptyState title="No roles" description="Create one to get started." />
          )}
          <div className="border-border border-t pt-5">
            <Pagination
              page={rolesResult.page}
              pathname="/admin/access-control"
              searchParams={{ tab: "roles", limit: String(pageQuery.limit) }}
            />
          </div>
        </>
      ) : null}

      {active === "permissions" && permissionsResult ? (
        <>
          {permissionsResult.data.length > 0 ? (
            <section
              aria-label="Permissions"
              className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
            >
              {permissionsResult.data.map((permission) => (
                <PermissionCard
                  key={permission.id}
                  permission={permission}
                  sessionPermissions={permissions}
                />
              ))}
            </section>
          ) : (
            <EmptyState
              title="No permissions"
              description="Create one to gate a new endpoint."
            />
          )}
          <div className="border-border border-t pt-5">
            <Pagination
              page={permissionsResult.page}
              pathname="/admin/access-control"
              searchParams={{ tab: "permissions", limit: String(pageQuery.limit) }}
            />
          </div>
        </>
      ) : null}

      {!activeResult ? (
        <EmptyState
          title="Nothing to show"
          description="Your account cannot view this section."
        />
      ) : null}
    </main>
  );
}
