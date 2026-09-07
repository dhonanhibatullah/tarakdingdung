"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api/client";
import {
  createStrategy,
  deleteStrategy,
  dryRunStrategy,
  updateStrategy,
  type StrategyMode,
} from "@/lib/api/strategies";
import { formBool, formText, parseJsonObject } from "@/lib/forms/parse";
import { requireSessionContext } from "@/lib/session";

import type { ActionResult } from "./state";

function fail(error: unknown): ActionResult {
  if (error instanceof ApiError) {
    return { status: "error", title: error.title, message: error.message };
  }
  return {
    status: "error",
    title: "Something went wrong",
    message: "The request could not be completed. Try again.",
  };
}

function denied(): ActionResult {
  return {
    status: "error",
    title: "Permission denied",
    message: "Your account cannot make this change.",
  };
}

function parseMode(raw: string): StrategyMode {
  return raw.toUpperCase() === "LIVE" ? "LIVE" : "PAPER";
}

const UNIVERSE_ROWS = 6;

function parseUniverse(formData: FormData) {
  const rows: { venue: string; base: string; quote: string }[] = [];
  for (let i = 0; i < UNIVERSE_ROWS; i += 1) {
    const base = formText(formData, `universe_base_${i}`).toUpperCase();
    const quote = formText(formData, `universe_quote_${i}`).toUpperCase();
    const venue =
      formText(formData, `universe_venue_${i}`).toUpperCase() || "INDODAX";
    if (base && quote) {
      rows.push({ venue, base, quote });
    }
  }
  return rows;
}

export async function createStrategyAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("strategy:add")) {
    return denied();
  }

  const name = formText(formData, "name");
  const kind = formText(formData, "kind") || "pipeline";
  const mode = parseMode(formText(formData, "mode"));
  const description = formText(formData, "description");
  const isEnabled = formBool(formData, "is_enabled");
  const universe = parseUniverse(formData);

  if (!name) {
    return { status: "error", title: "Check the form", message: "A name is required." };
  }
  if (universe.length === 0) {
    return {
      status: "error",
      title: "Check the form",
      message: "Add at least one symbol to the universe.",
    };
  }

  const parsed = parseJsonObject(formText(formData, "parameters"));
  if (!parsed.ok) {
    return {
      status: "error",
      title: "Check the parameters",
      message: parsed.error,
    };
  }

  try {
    await createStrategy({
      name,
      kind,
      mode,
      universe,
      description: description || undefined,
      parameters: parsed.value,
      is_enabled: isEnabled,
    });
  } catch (error) {
    return fail(error);
  }

  revalidatePath("/strategies");
  return {
    status: "success",
    title: "Strategy created",
    message: `${name} is ready. It runs in ${mode} mode.`,
  };
}

export async function setStrategyEnabledAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("strategy:set")) {
    return denied();
  }

  const id = formText(formData, "id");
  const enabled = formText(formData, "enabled") === "true";
  if (!id) {
    return { status: "error", title: "Missing strategy", message: "Refresh and retry." };
  }

  try {
    await updateStrategy(id, { is_enabled: enabled });
  } catch (error) {
    return fail(error);
  }

  revalidatePath("/strategies");
  return {
    status: "success",
    title: enabled ? "Strategy enabled" : "Strategy disabled",
    message: enabled
      ? "The engine will step it on the next cycle."
      : "The engine will skip it from the next cycle.",
  };
}

export async function deleteStrategyAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("strategy:remove")) {
    return denied();
  }

  const id = formText(formData, "id");
  const name = formText(formData, "name");
  const confirmation = formText(formData, "confirmation");
  if (!id || !name) {
    return { status: "error", title: "Missing strategy", message: "Refresh and retry." };
  }
  if (confirmation !== name) {
    return {
      status: "error",
      title: "Name does not match",
      message: `Type "${name}" exactly to confirm.`,
    };
  }

  try {
    await deleteStrategy(id);
  } catch (error) {
    return fail(error);
  }

  revalidatePath("/strategies");
  return {
    status: "success",
    title: "Strategy deleted",
    message: `${name} has been removed.`,
  };
}

export async function dryRunStrategyAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("engine:run")) {
    return denied();
  }

  const id = formText(formData, "id");
  if (!id) {
    return { status: "error", title: "Missing strategy", message: "Refresh and retry." };
  }

  try {
    const result = await dryRunStrategy(id);
    const halt = result.halted_by ? ` · halted by ${result.halted_by}` : "";
    return {
      status: "success",
      title: `Dry run: ${result.decision}`,
      message: `${result.orders} order(s) planned, ${result.rejected} rejected${halt}. Nothing was submitted.`,
    };
  } catch (error) {
    return fail(error);
  }
}
