import type { Metadata } from "next";

import Card from "@/components/ui/card";
import PageHeader from "@/components/ui/page-header";
import StatusBadge from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/states";
import { ApiError } from "@/lib/api/client";
import {
  getCurrentPortfolio,
  getEquityCurve,
  type CurrentPortfolioResponse,
  type EquityCurveResponse,
} from "@/lib/api/portfolio";
import { formatNumber, formatPercent, formatTimestamp } from "@/lib/format";
import { firstQueryValue, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";
import { windowFromDays } from "@/lib/time-window";

import EquitySparkline from "./_components/EquitySparkline";
import WindowFilter from "./_components/WindowFilter";

export const metadata: Metadata = {
  title: "Portfolio — Tarakdingdung",
  description: "Holdings and equity across every venue.",
};

interface PortfolioPageProps {
  searchParams: Promise<RawSearchParams>;
}

const DAY_OPTIONS = [7, 30, 90] as const;

export default async function PortfolioPage({
  searchParams,
}: PortfolioPageProps) {
  await requireAnyPermission(["portfolio:get"]);
  const raw = await searchParams;
  const days = Number(firstQueryValue(raw.days)) || 30;
  const win = windowFromDays(days);

  let current: CurrentPortfolioResponse | null = null;
  let equity: EquityCurveResponse = { points: [] };
  let loadError: string | null = null;

  try {
    [current, equity] = await Promise.all([
      getCurrentPortfolio(),
      getEquityCurve(win.start, win.end).catch(() => ({ points: [] })),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status >= 500)) {
      loadError =
        "No portfolio snapshot yet. It appears after the engine runs its first sync.";
    } else {
      throw error;
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Portfolio"
        description="Holdings and equity across every venue, from the latest sync."
      />

      {loadError || !current ? (
        <EmptyState title="Nothing synced yet" description={loadError ?? ""} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Equity" value={formatNumber(current.portfolio.equity)} />
            <Metric
              label="Equity peak"
              value={formatNumber(current.risk_state.equity_peak)}
            />
            <Metric
              label="Daily P&L"
              value={formatNumber(current.risk_state.daily_pnl)}
            />
            <Metric
              label="Realized volatility"
              value={formatPercent(current.risk_state.realized_volatility)}
            />
          </div>

          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-primary text-lg tracking-wide">
                Equity curve
              </h2>
              <div className="flex items-center gap-3">
                {current.risk_state.halted ? (
                  <StatusBadge variant="critical">Trading halted</StatusBadge>
                ) : (
                  <StatusBadge variant="success">Trading active</StatusBadge>
                )}
                <WindowFilter days={days} options={[...DAY_OPTIONS]} />
              </div>
            </div>
            <EquitySparkline points={equity.points} />
            <p className="text-muted-foreground text-xs">
              Last sync {formatTimestamp(current.portfolio.timestamp)}
            </p>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="space-y-3">
              <h2 className="font-display text-primary text-lg tracking-wide">
                Cash by venue
              </h2>
              {Object.keys(current.portfolio.cash).length > 0 ? (
                <dl className="space-y-2 text-sm">
                  {Object.entries(current.portfolio.cash).map(([venue, amount]) => (
                    <div key={venue} className="flex justify-between gap-4">
                      <dt className="text-muted-foreground">{venue}</dt>
                      <dd className="font-mono font-medium">
                        {formatNumber(amount)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-muted-foreground text-sm">No cash balances.</p>
              )}
            </Card>

            <Card className="space-y-3">
              <h2 className="font-display text-primary text-lg tracking-wide">
                Positions
              </h2>
              {current.portfolio.positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted-foreground text-left text-xs uppercase">
                        <th className="py-1.5 pr-4 font-semibold">Symbol</th>
                        <th className="py-1.5 pr-4 text-right font-semibold">
                          Quantity
                        </th>
                        <th className="py-1.5 text-right font-semibold">
                          Avg price
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {current.portfolio.positions.map((pos) => (
                        <tr
                          key={`${pos.symbol.venue}-${pos.symbol.base}-${pos.symbol.quote}`}
                          className="border-border border-t"
                        >
                          <td className="py-1.5 pr-4">
                            {pos.symbol.base}/{pos.symbol.quote}
                            <span className="text-muted-foreground ml-1 text-xs">
                              {pos.symbol.venue}
                            </span>
                          </td>
                          <td className="py-1.5 pr-4 text-right font-mono">
                            {formatNumber(pos.quantity, 8)}
                          </td>
                          <td className="py-1.5 text-right font-mono">
                            {formatNumber(pos.average_price, 8)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No open positions.</p>
              )}
            </Card>
          </div>
        </>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="space-y-1">
      <p className="text-muted-foreground text-xs font-semibold tracking-wider uppercase">
        {label}
      </p>
      <p className="font-display text-2xl tracking-wide">{value}</p>
    </Card>
  );
}
