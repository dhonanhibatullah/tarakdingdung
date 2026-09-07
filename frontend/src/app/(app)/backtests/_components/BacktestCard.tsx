import ResourceCard from "@/components/collection/ResourceCard";
import StatusBadge from "@/components/ui/status-badge";
import type { BacktestRunResponse } from "@/lib/api/backtests";
import { formatDateTime, formatNumber, formatSignedPercent } from "@/lib/format";

interface BacktestCardProps {
  run: BacktestRunResponse;
  strategyName?: string;
}

export default function BacktestCard({ run, strategyName }: BacktestCardProps) {
  const r = run.report;
  const positive = r.total_return >= 0;

  return (
    <ResourceCard
      title={strategyName ?? run.strategy_id}
      summary={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge variant={positive ? "success" : "critical"}>
            {formatSignedPercent(r.total_return)}
          </StatusBadge>
          <span className="text-muted-foreground text-xs">
            {formatDateTime(run.created_at)}
          </span>
        </div>
      }
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        <Row label="Sharpe" value={formatNumber(r.sharpe)} />
        <Row label="Sortino" value={formatNumber(r.sortino)} />
        <Row label="Max drawdown" value={formatSignedPercent(-Math.abs(r.max_drawdown))} />
        <Row label="Turnover" value={formatNumber(r.turnover)} />
        <Row label="Net return" value={formatSignedPercent(r.net_return)} />
        <Row label="Cost drag" value={formatSignedPercent(-Math.abs(r.cost_drag))} />
        <Row label="Trades" value={formatNumber(r.trade_count, 0)} />
        <Row label="Start equity" value={formatNumber(run.initial_equity)} />
      </dl>
    </ResourceCard>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono font-medium">{value}</dd>
    </div>
  );
}
