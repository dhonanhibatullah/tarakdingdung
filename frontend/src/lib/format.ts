// Shared value formatting for the read views. Money and quantities arrive as
// decimal strings; render them without imposing a currency.

export function formatNumber(
  value: string | number,
  maximumFractionDigits = 2,
): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) {
    return typeof value === "string" ? value : "—";
  }
  return n.toLocaleString(undefined, { maximumFractionDigits });
}

export function formatPercent(ratio: number, fractionDigits = 2): string {
  if (!Number.isFinite(ratio)) {
    return "—";
  }
  return `${(ratio * 100).toFixed(fractionDigits)}%`;
}

export function formatSignedPercent(ratio: number, fractionDigits = 2): string {
  const sign = ratio > 0 ? "+" : "";
  return `${sign}${formatPercent(ratio, fractionDigits)}`;
}

export function formatTimestamp(epochMs: number | string): string {
  const ms = typeof epochMs === "string" ? Number(epochMs) : epochMs;
  if (!Number.isFinite(ms) || ms <= 0) {
    return "—";
  }
  return new Date(ms).toLocaleString();
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}
