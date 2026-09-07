import Card from "@/components/ui/card";
import StatusBadge from "@/components/ui/status-badge";
import type { ValidationRunResponse } from "@/lib/api/validations";
import { formatDateTime, formatPercent } from "@/lib/format";

export default function ValidationVerdict({
  run,
  strategyName,
}: {
  run: ValidationRunResponse;
  strategyName?: string;
}) {
  const { overfitting } = run;

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-primary text-lg tracking-wide">
            {strategyName ?? run.strategy_id}
          </h2>
          <p className="text-muted-foreground text-xs">
            {run.trials} trials · {formatDateTime(run.created_at)}
          </p>
        </div>
        <StatusBadge variant={overfitting.passed ? "success" : "critical"}>
          {overfitting.passed ? "Passed" : "Failed"}
        </StatusBadge>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
        <Row label="PBO" value={formatPercent(overfitting.probability)} />
        <Row label="Threshold" value={formatPercent(overfitting.threshold)} />
        <Row label="Trials" value={String(run.trials)} />
      </dl>

      <p className="text-foreground/70 text-sm">
        {overfitting.passed
          ? "The probability of backtest overfitting is within the threshold. This is necessary evidence, not a guarantee — paper-trade before going live."
          : "The probability of backtest overfitting exceeds the threshold. Treat any live promotion of these parameters as a deliberate override."}
      </p>
      <p className="text-muted-foreground font-mono text-xs break-all">
        run id: {run.id}
      </p>
    </Card>
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
