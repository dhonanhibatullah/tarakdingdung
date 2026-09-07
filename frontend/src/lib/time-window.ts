// The backend works in epoch milliseconds (TimeRange in market.py). Helpers to
// turn "?days=30" style params and <input type="date"> values into a window.

const DAY_MS = 86_400_000;

export function windowFromDays(days: number, now: number = Date.now()): {
  start: number;
  end: number;
} {
  const span = Number.isFinite(days) && days > 0 ? days : 30;
  return { start: now - span * DAY_MS, end: now };
}

/** Parse a yyyy-mm-dd value to epoch ms at UTC midnight, or undefined. */
export function epochFromDateInput(value: string): number | undefined {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined;
  }
  const ms = Date.parse(`${value}T00:00:00Z`);
  return Number.isNaN(ms) ? undefined : ms;
}

/** yyyy-mm-dd for an epoch-ms value, for prefilling date inputs. */
export function dateInputValue(epochMs: number): string {
  return new Date(epochMs).toISOString().slice(0, 10);
}

/** yyyy-mm-dd pair from `lookbackDays` ago to today, for form defaults. */
export function dateInputWindow(lookbackDays: number): {
  start: string;
  end: string;
} {
  const now = Date.now();
  return {
    start: dateInputValue(now - lookbackDays * DAY_MS),
    end: dateInputValue(now),
  };
}
