"use client";

import { Play, Power, Trash2 } from "lucide-react";
import { useActionState, useEffect, useRef } from "react";

import Button from "@/components/ui/button";
import IconButton from "@/components/ui/icon-button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import { useActionFeedback } from "@/hooks/use-action-feedback";

import {
  deleteStrategyAction,
  dryRunStrategyAction,
  setStrategyEnabledAction,
} from "../_lib/actions";
import { INITIAL } from "../_lib/state";

interface StrategyActionsProps {
  id: string;
  name: string;
  isEnabled: boolean;
  canSet: boolean;
  canRun: boolean;
  canRemove: boolean;
}

export default function StrategyActions({
  id,
  name,
  isEnabled,
  canSet,
  canRun,
  canRemove,
}: StrategyActionsProps) {
  const [toggleState, toggleAction, togglePending] = useActionState(
    setStrategyEnabledAction,
    INITIAL,
  );
  const [dryRunState, dryRunAction, dryRunPending] = useActionState(
    dryRunStrategyAction,
    INITIAL,
  );
  const [deleteState, deleteAction, deletePending] = useActionState(
    deleteStrategyAction,
    INITIAL,
  );
  useActionFeedback(toggleState);
  useActionFeedback(dryRunState);
  useActionFeedback(deleteState);

  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (deleteState.status === "success") {
      dialogRef.current?.close();
    }
  }, [deleteState.status]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canSet ? (
        <form action={toggleAction}>
          <input type="hidden" name="id" value={id} />
          <input type="hidden" name="enabled" value={(!isEnabled).toString()} />
          <Button
            type="submit"
            variant={isEnabled ? "secondary" : "primary"}
            disabled={togglePending}
          >
            <Power aria-hidden="true" className="mr-1.5 size-4" />
            {isEnabled ? "Disable" : "Enable"}
          </Button>
        </form>
      ) : null}

      {canRun ? (
        <form action={dryRunAction}>
          <input type="hidden" name="id" value={id} />
          <Button type="submit" variant="secondary" disabled={dryRunPending}>
            <Play aria-hidden="true" className="mr-1.5 size-4" />
            {dryRunPending ? "Running…" : "Dry run"}
          </Button>
        </form>
      ) : null}

      {canRemove ? (
        <>
          <IconButton
            aria-label={`Delete ${name}`}
            onClick={() => dialogRef.current?.showModal()}
            className="text-critical hover:bg-critical/10"
          >
            <Trash2 aria-hidden="true" className="size-4" />
          </IconButton>

          <dialog
            ref={dialogRef}
            className="bg-background text-foreground m-auto w-[min(28rem,92vw)] rounded-2xl border border-[var(--border)] p-0 backdrop:bg-black/40"
          >
            <form action={deleteAction} className="space-y-4 p-6">
              <h2 className="font-display text-foreground text-xl tracking-wide">
                Delete strategy
              </h2>
              <p className="text-foreground/70 text-sm">
                This removes <span className="font-semibold">{name}</span>. Type
                its name to confirm.
              </p>
              <input type="hidden" name="id" value={id} />
              <input type="hidden" name="name" value={name} />
              <div>
                <Label htmlFor={`confirm-${id}`}>Strategy name</Label>
                <Input
                  id={`confirm-${id}`}
                  name="confirmation"
                  autoComplete="off"
                  placeholder={name}
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => dialogRef.current?.close()}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="critical" disabled={deletePending}>
                  {deletePending ? "Deleting…" : "Delete"}
                </Button>
              </div>
            </form>
          </dialog>
        </>
      ) : null}
    </div>
  );
}
