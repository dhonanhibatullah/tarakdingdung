import type { Metadata } from "next";
import { redirect } from "next/navigation";

import Pagination from "@/components/collection/Pagination";
import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";
import { listBacktests, type ListBacktestsQuery } from "@/lib/api/backtests";
import { listStrategies } from "@/lib/api/strategies";
import {
  getOutOfRangePageRedirect,
  parsePageQuery,
} from "@/lib/collection-query";
import { firstQueryValue, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";
import { dateInputWindow } from "@/lib/time-window";

import BacktestCard from "./_components/BacktestCard";
import BacktestFilters from "./_components/BacktestFilters";
import RunBacktestDialog from "./_components/RunBacktestDialog";

export const metadata: Metadata = {
  title: "Backtests — Tarakdingdung",
  description: "Replay a strategy over stored history.",
};

interface BacktestsPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function BacktestsPage({
  searchParams,
}: BacktestsPageProps) {
  const { permissions } = await requireAnyPermission(["backtest:get"]);
  const raw = await searchParams;
  const pageQuery = parsePageQuery(raw);
  const strategyId = firstQueryValue(raw.strategy_id) || undefined;

  const query: ListBacktestsQuery = {
    page: pageQuery.page,
    limit: pageQuery.limit,
    strategy_id: strategyId,
  };

  const canSeeStrategies = permissions.has("strategy:get");
  const [result, strategyList] = await Promise.all([
    listBacktests(query),
    canSeeStrategies
      ? listStrategies({ limit: 48 }).then((r) =>
          r.data.map((s) => ({ id: s.id, name: s.name })),
        )
      : Promise.resolve([] as { id: string; name: string }[]),
  ]);
  const nameById = new Map(strategyList.map((s) => [s.id, s.name]));
  const formWindow = dateInputWindow(180);

  const supportedParams: RawSearchParams = {
    page: raw.page,
    limit: String(pageQuery.limit),
    strategy_id: strategyId,
  };
  const outOfRange = getOutOfRangePageRedirect(
    "/backtests",
    supportedParams,
    result.page,
  );
  if (outOfRange) {
    redirect(outOfRange);
  }

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Backtests"
        description="Replay a strategy over stored candles and read its performance report."
        actions={
          permissions.has("backtest:add") ? (
            <RunBacktestDialog
              strategies={strategyList}
              defaultStart={formWindow.start}
              defaultEnd={formWindow.end}
            />
          ) : undefined
        }
      />

      <BacktestFilters strategyId={strategyId} strategies={strategyList} />

      <p className="text-muted-foreground px-1 text-xs font-semibold tracking-wider uppercase">
        Showing {result.data.length} of {result.page.total_items} runs
      </p>

      {result.data.length > 0 ? (
        <section
          aria-label="Backtest runs"
          className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
        >
          {result.data.map((run) => (
            <BacktestCard
              key={run.id}
              run={run}
              strategyName={nameById.get(run.strategy_id)}
            />
          ))}
        </section>
      ) : (
        <EmptyState
          title="No backtest runs"
          description={
            strategyId
              ? "No run matches this strategy filter."
              : permissions.has("backtest:add")
                ? "Run one to see how a strategy would have performed."
                : "Nothing has been run yet."
          }
        />
      )}

      <div className="border-border border-t pt-5">
        <Pagination
          page={result.page}
          pathname="/backtests"
          searchParams={{
            limit: String(pageQuery.limit),
            strategy_id: strategyId,
          }}
        />
      </div>
    </main>
  );
}
