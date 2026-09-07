"use client";

import { Play } from "lucide-react";
import { useActionState, useEffect, useRef } from "react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Select from "@/components/ui/select";
import { useActionFeedback } from "@/hooks/use-action-feedback";
import { INITIAL } from "@/lib/forms/result";

import { runBacktestAction } from "../_lib/actions";

interface RunBacktestDialogProps {
  strategies: { id: string; name: string }[];
  defaultStart: string;
  defaultEnd: string;
}

export default function RunBacktestDialog({
  strategies,
  defaultStart,
  defaultEnd,
}: RunBacktestDialogProps) {
  const [state, formAction, pending] = useActionState(
    runBacktestAction,
    INITIAL,
  );
  useActionFeedback(state);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (state.status === "success") {
      dialogRef.current?.close();
    }
  }, [state.status]);

  const start = defaultStart;
  const today = defaultEnd;

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        <Play aria-hidden="true" className="mr-1.5 size-4" />
        Run backtest
      </Button>

      <dialog
        ref={dialogRef}
        className="bg-background text-foreground m-auto w-[min(34rem,94vw)] rounded-2xl border border-[var(--border)] p-0 backdrop:bg-black/40"
      >
        <form action={formAction} className="max-h-[85vh] space-y-4 overflow-y-auto p-6">
          <h2 className="font-display text-primary text-2xl tracking-wide">
            Run backtest
          </h2>
          <p className="text-foreground/70 text-sm">
            Replays the strategy over stored candles. Nothing touches the market.
          </p>

          <div>
            <Label htmlFor="bt-strategy">Strategy</Label>
            {strategies.length > 0 ? (
              <Select id="bt-strategy" name="strategy_id" required>
                <option value="">Select a strategy…</option>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id="bt-strategy"
                name="strategy_id"
                required
                autoComplete="off"
                placeholder="Strategy UUID"
              />
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="bt-start">Window start</Label>
              <Input
                id="bt-start"
                name="window_start"
                type="date"
                defaultValue={start}
                required
              />
            </div>
            <div>
              <Label htmlFor="bt-end">Window end</Label>
              <Input
                id="bt-end"
                name="window_end"
                type="date"
                defaultValue={today}
                required
              />
            </div>
            <div>
              <Label htmlFor="bt-equity">Starting equity</Label>
              <Input
                id="bt-equity"
                name="initial_equity"
                inputMode="decimal"
                defaultValue="1000000"
                required
              />
            </div>
            <div>
              <Label htmlFor="bt-interval">Interval</Label>
              <Select id="bt-interval" name="interval" defaultValue="1h">
                {["1m", "5m", "15m", "1h", "4h", "1d"].map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </Select>
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="bt-completeness">
                Minimum coverage (0–1, optional)
              </Label>
              <Input
                id="bt-completeness"
                name="min_completeness"
                inputMode="decimal"
                placeholder="0.99"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              onClick={() => dialogRef.current?.close()}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Running…" : "Run backtest"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
