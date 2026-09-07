"use client";

import { useActionState } from "react";

import Button from "@/components/ui/button";
import Card from "@/components/ui/card";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Select from "@/components/ui/select";
import { useActionFeedback } from "@/hooks/use-action-feedback";
import { INITIAL } from "@/lib/forms/result";

import { runValidationAction } from "../_lib/actions";

interface RunValidationFormProps {
  strategies: { id: string; name: string }[];
  defaultStart: string;
  defaultEnd: string;
}

const DEFAULT_GRID = JSON.stringify(
  [
    { momentum_window: 48 },
    { momentum_window: 72 },
    { momentum_window: 96 },
  ],
  null,
  2,
);

export default function RunValidationForm({
  strategies,
  defaultStart,
  defaultEnd,
}: RunValidationFormProps) {
  const [state, formAction, pending] = useActionState(
    runValidationAction,
    INITIAL,
  );
  useActionFeedback(state);

  const start = defaultStart;
  const today = defaultEnd;

  return (
    <Card>
      <form action={formAction} className="space-y-4">
        <h2 className="font-display text-primary text-lg tracking-wide">
          Run walk-forward
        </h2>
        <p className="text-foreground/70 text-sm">
          Searches the parameter grid across time subsets and reports the
          probability of backtest overfitting (PBO). Below the threshold passes.
        </p>

        <div>
          <Label htmlFor="val-strategy">Strategy</Label>
          {strategies.length > 0 ? (
            <Select id="val-strategy" name="strategy_id" required>
              <option value="">Select a strategy…</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          ) : (
            <Input
              id="val-strategy"
              name="strategy_id"
              required
              autoComplete="off"
              placeholder="Strategy UUID"
            />
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="val-start">Window start</Label>
            <Input
              id="val-start"
              name="window_start"
              type="date"
              defaultValue={start}
              required
            />
          </div>
          <div>
            <Label htmlFor="val-end">Window end</Label>
            <Input
              id="val-end"
              name="window_end"
              type="date"
              defaultValue={today}
              required
            />
          </div>
          <div>
            <Label htmlFor="val-equity">Starting equity</Label>
            <Input
              id="val-equity"
              name="initial_equity"
              inputMode="decimal"
              defaultValue="1000000"
              required
            />
          </div>
          <div>
            <Label htmlFor="val-interval">Interval</Label>
            <Select id="val-interval" name="interval" defaultValue="1h">
              {["1m", "5m", "15m", "1h", "4h", "1d"].map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="val-subsets">Subsets</Label>
            <Input
              id="val-subsets"
              name="subsets"
              inputMode="numeric"
              defaultValue="8"
            />
          </div>
          <div>
            <Label htmlFor="val-threshold">PBO threshold</Label>
            <Input
              id="val-threshold"
              name="threshold"
              inputMode="decimal"
              defaultValue="0.1"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="val-grid">Parameter grid (JSON array)</Label>
          <textarea
            id="val-grid"
            name="parameter_grid"
            rows={8}
            defaultValue={DEFAULT_GRID}
            spellCheck={false}
            className="border-control-border bg-background text-foreground focus-visible:border-focus focus-visible:ring-focus w-full rounded-xl border px-3.5 py-2.5 font-mono text-xs transition-colors focus-visible:ring-2 focus-visible:outline-none"
          />
        </div>

        <div className="flex justify-end">
          <Button type="submit" disabled={pending}>
            {pending ? "Running…" : "Run walk-forward"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
