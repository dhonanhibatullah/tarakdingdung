"use server";

import { revalidatePath } from "next/cache";

import { runBacktest } from "@/lib/api/backtests";
import { formText } from "@/lib/forms/parse";
import {
  denied,
  fail,
  invalid,
  ok,
  type ActionResult,
} from "@/lib/forms/result";
import { requireSessionContext } from "@/lib/session";
import { epochFromDateInput } from "@/lib/time-window";

export async function runBacktestAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("backtest:add")) {
    return denied();
  }

  const strategyId = formText(formData, "strategy_id");
  const start = epochFromDateInput(formText(formData, "window_start"));
  const end = epochFromDateInput(formText(formData, "window_end"));
  const initialEquity = formText(formData, "initial_equity");
  const interval = formText(formData, "interval") || "1h";
  const minCompletenessRaw = formText(formData, "min_completeness");

  if (!strategyId) {
    return invalid("Choose a strategy.");
  }
  if (start === undefined || end === undefined || start >= end) {
    return invalid("Give a start date before the end date.");
  }
  if (!initialEquity || Number(initialEquity) <= 0) {
    return invalid("Enter a positive starting equity.");
  }

  try {
    const run = await runBacktest({
      strategy_id: strategyId,
      window_start: start,
      window_end: end,
      initial_equity: initialEquity,
      interval,
      min_completeness: minCompletenessRaw
        ? Number(minCompletenessRaw)
        : undefined,
    });
    revalidatePath("/backtests");
    return ok(
      "Backtest complete",
      `${(run.report.total_return * 100).toFixed(2)}% return over ${run.report.trade_count} trades.`,
    );
  } catch (error) {
    return fail(error);
  }
}
