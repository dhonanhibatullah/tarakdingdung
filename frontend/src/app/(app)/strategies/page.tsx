import type { Metadata } from "next";
import { redirect } from "next/navigation";

import Pagination from "@/components/collection/Pagination";
import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";
import { listStrategies, type ListStrategiesQuery } from "@/lib/api/strategies";
import {
  getOutOfRangePageRedirect,
  parsePageQuery,
} from "@/lib/collection-query";
import { firstQueryValue, parseEnumQuery, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";

import NewStrategyDialog from "./_components/NewStrategyDialog";
import StrategyCard from "./_components/StrategyCard";
import StrategyFilters from "./_components/StrategyFilters";

export const metadata: Metadata = {
  title: "Strategies — Tarakdingdung",
  description: "Pipelines the engine runs each cycle.",
};

interface StrategiesPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function StrategiesPage({
  searchParams,
}: StrategiesPageProps) {
  const { permissions } = await requireAnyPermission(["strategy:get"]);
  const raw = await searchParams;
  const pageQuery = parsePageQuery(raw);
  const mode = parseEnumQuery(firstQueryValue(raw.mode), ["PAPER", "LIVE"] as const);

  const query: ListStrategiesQuery = { ...pageQuery, mode };
  const result = await listStrategies(query);

  const supportedParams: RawSearchParams = {
    page: raw.page,
    limit: String(pageQuery.limit),
    search: pageQuery.search,
    mode,
  };
  const outOfRange = getOutOfRangePageRedirect(
    "/strategies",
    supportedParams,
    result.page,
  );
  if (outOfRange) {
    redirect(outOfRange);
  }

  const paginationParams: RawSearchParams = {
    limit: String(pageQuery.limit),
    search: pageQuery.search,
    mode,
  };
  const cardPermissions = [...permissions];

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Strategies"
        description="Pipelines the engine runs each cycle."
        actions={
          permissions.has("strategy:add") ? <NewStrategyDialog /> : undefined
        }
      />

      <StrategyFilters search={pageQuery.search} mode={mode} />

      <p className="text-muted-foreground px-1 text-xs font-semibold tracking-wider uppercase">
        Showing {result.data.length} of {result.page.total_items} strategies
      </p>

      {result.data.length > 0 ? (
        <section
          aria-label="Strategies"
          className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
        >
          {result.data.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              permissions={cardPermissions}
            />
          ))}
        </section>
      ) : (
        <EmptyState
          title="No strategies"
          description={
            pageQuery.search || mode
              ? "No strategy matches the current filters."
              : permissions.has("strategy:add")
                ? "Create one to give the engine something to run."
                : "Nothing has been created yet."
          }
        />
      )}

      <div className="border-border border-t pt-5">
        <Pagination
          page={result.page}
          pathname="/strategies"
          searchParams={paginationParams}
        />
      </div>
    </main>
  );
}
