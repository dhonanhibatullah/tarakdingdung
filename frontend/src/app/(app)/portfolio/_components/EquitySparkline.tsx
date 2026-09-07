import type { EquityPointResponse } from "@/lib/api/portfolio";
import { formatNumber, formatTimestamp } from "@/lib/format";

interface EquitySparklineProps {
  points: EquityPointResponse[];
}

const WIDTH = 720;
const HEIGHT = 160;
const PAD = 8;

export default function EquitySparkline({ points }: EquitySparklineProps) {
  if (points.length < 2) {
    return (
      <p className="text-muted-foreground text-sm">
        Not enough equity history in this window to draw a curve.
      </p>
    );
  }

  const values = points.map((p) => Number(p.equity));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const path = points
    .map((p, i) => {
      const x = PAD + (i / (points.length - 1)) * (WIDTH - 2 * PAD);
      const y =
        HEIGHT - PAD - ((Number(p.equity) - min) / span) * (HEIGHT - 2 * PAD);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const first = values[0];
  const last = values[values.length - 1];
  const up = last >= first;

  return (
    <figure className="space-y-2">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="border-border bg-background w-full rounded-xl border"
        role="img"
        aria-label={`Equity from ${formatNumber(first)} to ${formatNumber(last)}`}
        preserveAspectRatio="none"
      >
        <path
          d={path}
          fill="none"
          stroke={up ? "var(--success)" : "var(--critical)"}
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <figcaption className="text-muted-foreground flex justify-between text-xs">
        <span>{formatTimestamp(points[0].timestamp)}</span>
        <span>
          {formatNumber(first)} → {formatNumber(last)}
        </span>
        <span>{formatTimestamp(points[points.length - 1].timestamp)}</span>
      </figcaption>
    </figure>
  );
}
