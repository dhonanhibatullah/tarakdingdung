import type { Metadata } from "next";

import FilterBar from "@/components/collection/FilterBar";
import Card from "@/components/ui/card";
import Input from "@/components/ui/input";
import PageHeader from "@/components/ui/page-header";
import Select from "@/components/ui/select";
import StatusBadge from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/states";
import { ApiError } from "@/lib/api/client";
import { getCoverage, type CoverageResponse } from "@/lib/api/market-data";
import { formatNumber, formatPercent, formatTimestamp } from "@/lib/format";
import { firstQueryValue, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";
import { windowFromDays } from "@/lib/time-window";

export const metadata: Metadata = {
  title: "Market Data — Tarakdingdung",
  description: "Candle coverage per symbol and interval.",
};

interface MarketDataPageProps {
  searchParams: Promise<RawSearchParams>;
}

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const DAY_CHOICES = [1, 7, 30, 90] as const;
const DEFAULTS = { venue: "INDODAX", base: "BTC", quote: "IDR", interval: "1h", days: 7 };

export default async function MarketDataPage({
  searchParams,
}: MarketDataPageProps) {
  await requireAnyPermission(["market_data:get"]);
  const raw = await searchParams;

  const venue = (firstQueryValue(raw.venue) || DEFAULTS.venue).toUpperCase();
  const base = (firstQueryValue(raw.base) || DEFAULTS.base).toUpperCase();
  const quote = (firstQueryValue(raw.quote) || DEFAULTS.quote).toUpperCase();
  const interval = firstQueryValue(raw.interval) || DEFAULTS.interval;
  const days = Number(firstQueryValue(raw.days)) || DEFAULTS.days;
  const win = windowFromDays(days);

  let coverage: CoverageResponse | null = null;
  let loadError: string | null = null;
  try {
    coverage = await getCoverage({
      venue,
      base,
      quote,
      interval,
      window_start: win.start,
      window_end: win.end,
    });
  } catch (error) {
    loadError =
      error instanceof ApiError
        ? error.message
        : "The coverage check could not be completed.";
  }

  const completeness = coverage?.completeness ?? 0;
  const variant =
    completeness >= 0.99 ? "success" : completeness >= 0.9 ? "warning" : "critical";

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Market Data"
        description="How complete the stored candle history is — run this before trusting a backtest over a window."
      />

      <FilterBar clearHref="/market-data">
        <label>
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Venue
          </span>
          <Input name="venue" defaultValue={venue} aria-label="Venue" />
        </label>
        <label>
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Base
          </span>
          <Input name="base" defaultValue={base} aria-label="Base asset" />
        </label>
        <label>
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Quote
          </span>
          <Input name="quote" defaultValue={quote} aria-label="Quote asset" />
        </label>
        <label>
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Interval
          </span>
          <Select name="interval" defaultValue={interval} aria-label="Interval">
            {INTERVALS.map((i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </Select>
        </label>
        <label>
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Window
          </span>
          <Select
            name="days"
            defaultValue={String(days)}
            aria-label="Look-back window in days"
          >
            {DAY_CHOICES.map((d) => (
              <option key={d} value={d}>
                Last {d} day{d === 1 ? "" : "s"}
              </option>
            ))}
          </Select>
        </label>
      </FilterBar>

      {loadError || !coverage ? (
        <EmptyState
          title="No coverage report"
          description={loadError ?? "Adjust the filters and apply."}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Symbol" value={`${coverage.symbol.base}/${coverage.symbol.quote}`} />
            <Metric label="Expected candles" value={formatNumber(coverage.expected, 0)} />
            <Metric label="Present candles" value={formatNumber(coverage.present, 0)} />
            <Card className="space-y-1">
              <p className="text-muted-foreground text-xs font-semibold tracking-wider uppercase">
                Completeness
              </p>
              <div className="flex items-center gap-2">
                <span className="font-display text-2xl tracking-wide">
                  {formatPercent(coverage.completeness)}
                </span>
                <StatusBadge variant={variant}>
                  {variant === "success"
                    ? "Backtest-ready"
                    : variant === "warning"
                      ? "Gaps present"
                      : "Sparse"}
                </StatusBadge>
              </div>
            </Card>
          </div>

          <Card className="space-y-3">
            <h2 className="font-display text-primary text-lg tracking-wide">
              Gaps ({coverage.gaps.length})
            </h2>
            {coverage.gaps.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted-foreground text-left text-xs uppercase">
                      <th className="py-1.5 pr-4 font-semibold">From</th>
                      <th className="py-1.5 font-semibold">To</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverage.gaps.map((gap, i) => (
                      <tr key={i} className="border-border border-t">
                        <td className="py-1.5 pr-4 font-mono">
                          {formatTimestamp(gap.start)}
                        </td>
                        <td className="py-1.5 font-mono">
                          {formatTimestamp(gap.end)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                No gaps in this window — every expected candle is stored.
              </p>
            )}
          </Card>
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
