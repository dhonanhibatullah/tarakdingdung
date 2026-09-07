import type { Metadata } from "next";

import FilterBar from "@/components/collection/FilterBar";
import Input from "@/components/ui/input";
import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";
import { ApiError } from "@/lib/api/client";
import { listStrategies } from "@/lib/api/strategies";
import {
  getValidation,
  type ValidationRunResponse,
} from "@/lib/api/validations";
import { firstQueryValue, type RawSearchParams } from "@/lib/query";
import { requireAnyPermission } from "@/lib/session";
import { dateInputWindow } from "@/lib/time-window";

import RunValidationForm from "./_components/RunValidationForm";
import ValidationVerdict from "./_components/ValidationVerdict";

export const metadata: Metadata = {
  title: "Validations — Tarakdingdung",
  description: "Walk-forward search with an overfitting gate.",
};

interface ValidationsPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function ValidationsPage({
  searchParams,
}: ValidationsPageProps) {
  const { permissions } = await requireAnyPermission(["backtest:get"]);
  const raw = await searchParams;
  const lookupId = firstQueryValue(raw.id)?.trim();

  const canSeeStrategies = permissions.has("strategy:get");
  const strategyList = canSeeStrategies
    ? await listStrategies({ limit: 48 }).then((r) =>
        r.data.map((s) => ({ id: s.id, name: s.name })),
      )
    : [];
  const nameById = new Map(strategyList.map((s) => [s.id, s.name]));
  const validationWindow = dateInputWindow(365);

  let run: ValidationRunResponse | null = null;
  let lookupError: string | null = null;
  if (lookupId) {
    try {
      run = await getValidation(lookupId);
    } catch (error) {
      lookupError =
        error instanceof ApiError && error.status === 404
          ? `No validation run with id ${lookupId}.`
          : error instanceof ApiError
            ? error.message
            : "That validation run could not be loaded.";
    }
  }

  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Validations"
        description="Walk-forward parameter search with a probability-of-backtest-overfitting gate. Runs are retrieved by id — keep the id a run returns."
      />

      <FilterBar clearHref="/validations" applyLabel="Look up">
        <label className="sm:col-span-2 lg:col-span-3">
          <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
            Validation run id
          </span>
          <Input
            name="id"
            defaultValue={lookupId}
            placeholder="UUID from a previous run"
            aria-label="Validation run id"
          />
        </label>
      </FilterBar>

      {lookupError ? (
        <EmptyState title="Not found" description={lookupError} />
      ) : run ? (
        <ValidationVerdict run={run} strategyName={nameById.get(run.strategy_id)} />
      ) : null}

      {permissions.has("backtest:add") ? (
        <RunValidationForm
          strategies={strategyList}
          defaultStart={validationWindow.start}
          defaultEnd={validationWindow.end}
        />
      ) : (
        <EmptyState
          title="Read-only"
          description="Your account can view validation runs by id but cannot start one."
        />
      )}
    </main>
  );
}
