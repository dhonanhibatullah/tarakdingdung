"use client";

import { Plus } from "lucide-react";
import { useActionState, useEffect, useRef } from "react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Select from "@/components/ui/select";
import { useActionFeedback } from "@/hooks/use-action-feedback";

import { createStrategyAction } from "../_lib/actions";
import { INITIAL } from "../_lib/state";

const DEFAULT_PARAMETERS = JSON.stringify(
  {
    signal: "momentum",
    allocator: "equal_weight",
    long_only: true,
    max_gross: 0.6,
    max_positions: 2,
    momentum_window: 72,
    fast_window: 24,
    slow_window: 72,
    volatility_window: 72,
    rebalance_band: 0.02,
    max_position: 0.3,
    max_asset: 0.35,
    max_venue: 1.0,
    max_volatility: 0.2,
    max_drawdown: 0.15,
    max_daily_loss: 0.04,
  },
  null,
  2,
);

const UNIVERSE_ROWS = [0, 1, 2, 3, 4, 5] as const;

export default function NewStrategyDialog() {
  const [state, formAction, pending] = useActionState(
    createStrategyAction,
    INITIAL,
  );
  useActionFeedback(state);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (state.status === "success") {
      dialogRef.current?.close();
    }
  }, [state.status]);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        <Plus aria-hidden="true" className="mr-1.5 size-4" />
        New strategy
      </Button>

      <dialog
        ref={dialogRef}
        className="bg-background text-foreground m-auto w-[min(40rem,94vw)] rounded-2xl border border-[var(--border)] p-0 backdrop:bg-black/40"
      >
        <form action={formAction} className="max-h-[85vh] space-y-4 overflow-y-auto p-6">
          <h2 className="font-display text-primary text-2xl tracking-wide">
            New strategy
          </h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" name="name" required autoComplete="off" />
            </div>
            <div>
              <Label htmlFor="kind">Kind</Label>
              <Select id="kind" name="kind" defaultValue="pipeline">
                <option value="pipeline">pipeline</option>
                <option value="buy_and_hold">buy_and_hold</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="mode">Mode</Label>
              <Select id="mode" name="mode" defaultValue="PAPER">
                <option value="PAPER">Paper (simulated)</option>
                <option value="LIVE">Live (real orders)</option>
              </Select>
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" name="description" autoComplete="off" />
            </div>
          </div>

          <fieldset className="border-border rounded-xl border p-3">
            <legend className="text-foreground/70 px-1 text-xs font-semibold">
              Universe — leave a row blank to skip it
            </legend>
            <div className="space-y-2">
              {UNIVERSE_ROWS.map((i) => (
                <div key={i} className="grid grid-cols-3 gap-2">
                  <Input
                    name={`universe_venue_${i}`}
                    defaultValue={i < 3 ? "INDODAX" : ""}
                    placeholder="Venue"
                    aria-label={`Row ${i + 1} venue`}
                  />
                  <Input
                    name={`universe_base_${i}`}
                    placeholder="Base (BTC)"
                    aria-label={`Row ${i + 1} base`}
                  />
                  <Input
                    name={`universe_quote_${i}`}
                    placeholder="Quote (IDR)"
                    aria-label={`Row ${i + 1} quote`}
                  />
                </div>
              ))}
            </div>
          </fieldset>

          <div>
            <Label htmlFor="parameters">Parameters (JSON)</Label>
            <textarea
              id="parameters"
              name="parameters"
              rows={12}
              defaultValue={DEFAULT_PARAMETERS}
              spellCheck={false}
              className="border-control-border bg-background text-foreground focus-visible:border-focus focus-visible:ring-focus w-full rounded-xl border px-3.5 py-2.5 font-mono text-xs transition-colors focus-visible:ring-2 focus-visible:outline-none"
            />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="is_enabled" className="size-4" />
            Enable immediately (the engine steps it once cron is on)
          </label>

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              onClick={() => dialogRef.current?.close()}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Creating…" : "Create strategy"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
