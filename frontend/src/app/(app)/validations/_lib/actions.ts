"use server";

import { redirect } from "next/navigation";

import { runValidation } from "@/lib/api/validations";
import { formText } from "@/lib/forms/parse";
import {
  denied,
  fail,
  invalid,
  type ActionResult,
} from "@/lib/forms/result";
import { requireSessionContext } from "@/lib/session";
import { epochFromDateInput } from "@/lib/time-window";

function parseGrid(
  raw: string,
): { ok: true; value: Record<string, unknown>[] } | { ok: false; error: string } {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      !Array.isArray(parsed) ||
      parsed.length === 0 ||
      parsed.some((item) => !item || typeof item !== "object" || Array.isArray(item))
    ) {
      return { ok: false, error: "Enter a non-empty JSON array of objects." };
    }
    return { ok: true, value: parsed as Record<string, unknown>[] };
  } catch {
    return { ok: false, error: "The parameter grid is not valid JSON." };
  }
}

export async function runValidationAction(
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
  const subsetsRaw = formText(formData, "subsets");
  const thresholdRaw = formText(formData, "threshold");

  if (!strategyId) {
    return invalid("Choose a strategy.");
  }
  if (start === undefined || end === undefined || start >= end) {
    return invalid("Give a start date before the end date.");
  }
  if (!initialEquity || Number(initialEquity) <= 0) {
    return invalid("Enter a positive starting equity.");
  }
  const grid = parseGrid(formText(formData, "parameter_grid"));
  if (!grid.ok) {
    return invalid(grid.error);
  }

  let runId: string;
  try {
    const run = await runValidation({
      strategy_id: strategyId,
      window_start: start,
      window_end: end,
      initial_equity: initialEquity,
      parameter_grid: grid.value,
      interval,
      subsets: subsetsRaw ? Number(subsetsRaw) : undefined,
      threshold: thresholdRaw ? Number(thresholdRaw) : undefined,
    });
    runId = run.id;
  } catch (error) {
    return fail(error);
  }

  redirect(`/validations?id=${runId}`);
}
