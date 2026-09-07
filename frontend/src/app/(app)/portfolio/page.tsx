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
import VenueSelect from "./_components/VenueSelect";
import WindowFilter from "./_components/WindowFilter";

export const metadata: Metadata = {
  title: "Portfolio — Tarakdingdung",
  description: "Holdings and equity per venue.",
};

interface PortfolioPageProps {
  searchParams: Promise<RawSearchParams>;
}

const DAY_OPTIONS = [7, 30, 90] as const;

function isSoftError(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 404 || error.status >= 500)
  );
}

export default async function PortfolioPage({
  searchParams,
}: PortfolioPageProps) {
  await requireAnyPermission(["portfolio:get"]);
  const raw = await searchParams;
  const days = Number(firstQueryValue(raw.days)) || 30;
  const requestedVenue = firstQueryValue(raw.venue)?.toUpperCase();
  const win = windowFromDays(days);

  // One unscoped read to learn the venue list, then everything is fetched
  // scoped to the active venue so the whole page follows the toggle.
  let overview: CurrentPortfolioResponse | null = null;
  let loadError: string | null = null;
  try {
    overview = await getCurrentPortfolio();
  } catch (error) {
    if (isSoftError(error)) {
      loadError =
        "No portfolio snapshot yet. It appears after the engine runs its first sync.";
    } else {
      throw error;
    }
  }

  const venues = overview
    ? (Object.keys(overview.portfolio.equity_by_venue).length
        ? Object.keys(overview.portfolio.equity_by_venue)
        : Object.keys(overview.portfolio.balances)
      ).sort()
    : [];
  const activeVenue =
    requestedVenue && venues.includes(requestedVenue)
      ? requestedVenue
      : (venues[0] ?? "");

  let current = overview;
  let equity: EquityCurveResponse = { points: [] };
  if (overview && activeVenue) {
    try {
      [current, equity] = await Promise.all([
        getCurrentPortfolio(activeVenue),
        getEquityCurve(win.start, win.end, activeVenue).catch(() => ({
          points: [],
        })),
      ]);
    } catch (error) {
      if (!isSoftError(error)) {
        throw error;
      }
    }
  }

  const venueAssets = current
    ? Object.entries(current.portfolio.balances[activeVenue] ?? {}).sort(
        ([a], [b]) => a.localeCompare(b),
      )
    : [];
  const venuePositions =
    current?.portfolio.positions.filter(
      (pos) => !activeVenue || pos.symbol.venue === activeVenue,
    ) ?? [];

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Portfolio"
        description="Equity, holdings and history for one venue at a time."
        actions={
          venues.length > 1 ? (
            <VenueSelect venues={venues} active={activeVenue} days={days} />
          ) : undefined
        }
      />

      {loadError || !current ? (
        <EmptyState title="Nothing synced yet" description={loadError ?? ""} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric
              label={`Equity${activeVenue ? ` · ${activeVenue}` : ""}`}
              value={formatNumber(current.portfolio.equity)}
            />
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
                Equity curve{activeVenue ? ` · ${activeVenue}` : ""}
              </h2>
              <div className="flex items-center gap-3">
                {current.risk_state.halted ? (
                  <StatusBadge variant="critical">Trading halted</StatusBadge>
                ) : (
                  <StatusBadge variant="success">Trading active</StatusBadge>
                )}
                <WindowFilter
                  days={days}
                  options={[...DAY_OPTIONS]}
                  venue={activeVenue || undefined}
                />
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
                Balances
              </h2>
              {venueAssets.length > 0 ? (
                <dl className="space-y-2 text-sm">
                  {venueAssets.map(([asset, amount]) => (
                    <div key={asset} className="flex justify-between gap-4">
                      <dt className="text-muted-foreground">{asset}</dt>
                      <dd className="font-mono font-medium">
                        {formatNumber(amount, 8)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-muted-foreground text-sm">
                  {venues.length === 0
                    ? "The last sync recorded no venue balances."
                    : `Nothing reported on ${activeVenue}.`}
                </p>
              )}
              <p className="text-muted-foreground text-xs">
                Free balance the venue reported. Equity counts priced positions
                plus the IDR balance — other currencies stay out of it.
              </p>
            </Card>

            <Card className="space-y-3">
              <h2 className="font-display text-primary text-lg tracking-wide">
                Positions
              </h2>
              {venuePositions.length > 0 ? (
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
                      {venuePositions.map((pos) => (
                        <tr
                          key={`${pos.symbol.venue}-${pos.symbol.base}-${pos.symbol.quote}`}
                          className="border-border border-t"
                        >
                          <td className="py-1.5 pr-4">
                            {pos.symbol.base}/{pos.symbol.quote}
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
                <p className="text-muted-foreground text-sm">
                  No open positions{activeVenue ? ` on ${activeVenue}` : ""}.
                </p>
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
