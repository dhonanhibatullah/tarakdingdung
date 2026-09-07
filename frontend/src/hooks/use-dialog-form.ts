"use client";

import { useActionState, useEffect, useRef } from "react";

import { useActionFeedback } from "@/hooks/use-action-feedback";
import { INITIAL, type ActionResult } from "@/lib/forms/result";

type DialogAction = (
  prev: ActionResult,
  formData: FormData,
) => Promise<ActionResult>;

/** Wires a server action to a <dialog>: toast on settle, close on success. */
export function useDialogForm(action: DialogAction) {
  const [state, formAction, pending] = useActionState(action, INITIAL);
  useActionFeedback(state);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (state.status === "success") {
      dialogRef.current?.close();
    }
  }, [state.status]);

  return { state, formAction, pending, dialogRef };
}
