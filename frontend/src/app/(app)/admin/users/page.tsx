import type { Metadata } from "next";
import { redirect } from "next/navigation";

import Pagination from "@/components/collection/Pagination";
import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";
import { listRoles } from "@/lib/api/roles";
import { listUsers, type ListUsersQuery } from "@/lib/api/users";
import {
  getOutOfRangePageRedirect,
  parsePageQuery,
} from "@/lib/collection-query";
import { firstQueryValue, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";

import NewUserDialog from "./_components/NewUserDialog";
import UserCard from "./_components/UserCard";
import UserFilters from "./_components/UserFilters";

export const metadata: Metadata = {
  title: "Users — Tarakdingdung",
  description: "People with access to the console.",
};

interface UsersPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function UsersPage({ searchParams }: UsersPageProps) {
  const { permissions } = await requireAnyPermission(["user:get"]);
  const raw = await searchParams;
  const pageQuery = parsePageQuery(raw);
  const roleId = firstQueryValue(raw.role_id) || undefined;

  const query: ListUsersQuery = { ...pageQuery, role_id: roleId };
  const canSeeRoles = permissions.has("role:get");
  const [result, roleList] = await Promise.all([
    listUsers(query),
    canSeeRoles
      ? listRoles({ limit: 48 }).then((r) =>
          r.data.map((role) => ({ id: role.id, name: role.name })),
        )
      : Promise.resolve([] as { id: string; name: string }[]),
  ]);

  const supportedParams: RawSearchParams = {
    page: raw.page,
    limit: String(pageQuery.limit),
    search: pageQuery.search,
    role_id: roleId,
  };
  const outOfRange = getOutOfRangePageRedirect(
    "/admin/users",
    supportedParams,
    result.page,
  );
  if (outOfRange) {
    redirect(outOfRange);
  }

  const canCreate = permissions.has("user:add") && roleList.length > 0;

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Users"
        description="Accounts that can sign in to the console, and the role each one carries."
        actions={canCreate ? <NewUserDialog roles={roleList} /> : undefined}
      />

      <UserFilters
        search={pageQuery.search}
        roleId={roleId}
        roles={roleList}
      />

      <p className="text-muted-foreground px-1 text-xs font-semibold tracking-wider uppercase">
        Showing {result.data.length} of {result.page.total_items} users
      </p>

      {result.data.length > 0 ? (
        <section
          aria-label="Users"
          className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
        >
          {result.data.map((user) => (
            <UserCard
              key={user.id}
              user={user}
              roles={roleList}
              permissions={permissions}
            />
          ))}
        </section>
      ) : (
        <EmptyState
          title="No users"
          description={
            pageQuery.search || roleId
              ? "No user matches the current filters."
              : "Nothing has been created yet."
          }
        />
      )}

      <div className="border-border border-t pt-5">
        <Pagination
          page={result.page}
          pathname="/admin/users"
          searchParams={{
            limit: String(pageQuery.limit),
            search: pageQuery.search,
            role_id: roleId,
          }}
        />
      </div>
    </main>
  );
}
