import ResourceCard from "@/components/collection/ResourceCard";
import StatusBadge from "@/components/ui/status-badge";
import type { StrategyResponse } from "@/lib/api/strategies";

import StrategyActions from "./StrategyActions";

interface StrategyCardProps {
  strategy: StrategyResponse;
  permissions: readonly string[];
}

function paramLine(parameters: Record<string, unknown>): string {
  const keys = ["signal", "allocator", "momentum_window", "max_gross", "rebalance_band"];
  const parts = keys
    .filter((key) => parameters[key] !== undefined)
    .map((key) => `${key}=${String(parameters[key])}`);
  return parts.length > 0 ? parts.join(" · ") : "default parameters";
}

export default function StrategyCard({
  strategy,
  permissions,
}: StrategyCardProps) {
  const perms = new Set(permissions);

  return (
    <ResourceCard
      title={strategy.name}
      summary={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge variant={strategy.mode === "LIVE" ? "warning" : "info"}>
            {strategy.mode}
          </StatusBadge>
          <StatusBadge variant={strategy.is_enabled ? "success" : "neutral"}>
            {strategy.is_enabled ? "Enabled" : "Disabled"}
          </StatusBadge>
        </div>
      }
    >
      <dl className="space-y-2.5">
        <div className="flex items-start justify-between gap-4">
          <dt className="text-muted-foreground">Kind</dt>
          <dd className="text-right font-medium">{strategy.kind}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="text-muted-foreground">Universe</dt>
          <dd className="min-w-0 text-right font-medium break-words">
            {strategy.universe.length > 0
              ? strategy.universe
                  .map((s) => `${s.base}/${s.quote}`)
                  .join(", ")
              : "—"}
          </dd>
        </div>
      </dl>

      <p className="text-foreground/70 mt-3 line-clamp-3">
        {strategy.description || "No description."}
      </p>
      <p className="text-muted-foreground mt-2 font-mono text-xs break-words">
        {paramLine(strategy.parameters)}
      </p>

      <div className="mt-5">
        <StrategyActions
          id={strategy.id}
          name={strategy.name}
          isEnabled={strategy.is_enabled}
          canSet={perms.has("strategy:set")}
          canRun={perms.has("engine:run")}
          canRemove={perms.has("strategy:remove")}
        />
      </div>
    </ResourceCard>
  );
}
