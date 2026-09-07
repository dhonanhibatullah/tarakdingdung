import StatusBadge, { type StatusVariant } from "@/components/ui/status-badge";

interface Cycle {
  strategy: string;
  decision: string;
  detail: string;
  when: string;
  variant: StatusVariant;
}

const CYCLES: readonly Cycle[] = [
  {
    strategy: "idx-momentum",
    decision: "Traded",
    detail: "2 orders · BTC/IDR, ETH/IDR",
    when: "6 min ago",
    variant: "success",
  },
  {
    strategy: "idx-meanrev",
    decision: "No drift",
    detail: "within the no-trade band",
    when: "6 min ago",
    variant: "neutral",
  },
  {
    strategy: "tko-carry",
    decision: "Halted",
    detail: "DailyLossHaltRiskRule",
    when: "1 h ago",
    variant: "critical",
  },
  {
    strategy: "idx-momentum",
    decision: "Traded",
    detail: "1 order · SOL/IDR",
    when: "1 h ago",
    variant: "success",
  },
];

export default function RecentCycles() {
  return (
    <section aria-labelledby="recent-cycles-heading">
      <h2
        id="recent-cycles-heading"
        className="font-display text-primary text-2xl tracking-wide"
      >
        Recent cycles
      </h2>
      <p className="text-muted-foreground mt-1 text-sm">
        The last decisions the engine made, newest first.
      </p>
      <ul className="border-border divide-border bg-surface mt-4 divide-y rounded-2xl border shadow-sm">
        {CYCLES.map((cycle, index) => (
          <li
            key={`${cycle.strategy}-${index}`}
            className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="text-foreground font-semibold">{cycle.strategy}</p>
              <p className="text-muted-foreground mt-0.5 text-xs">
                {cycle.detail}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <StatusBadge variant={cycle.variant}>
                {cycle.decision}
              </StatusBadge>
              <span className="text-muted-foreground text-xs">{cycle.when}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
