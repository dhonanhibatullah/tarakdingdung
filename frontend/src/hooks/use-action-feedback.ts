"use client";

import { useContext, useEffect, useRef } from "react";

import { ToastContext } from "@/components/ui/toast-provider";
import type { ActionState } from "@/lib/forms/action-state";

/** Fires a toast whenever a server-action state transitions to error/success. */
export function useActionFeedback(state: ActionState<string>): void {
  const toast = useContext(ToastContext);
  const shown = useRef<ActionState<string> | null>(null);

  useEffect(() => {
    if (
      !toast ||
      state.status === "idle" ||
      !state.title ||
      shown.current === state
    ) {
      return;
    }
    shown.current = state;
    const message = state.message ?? "";
    if (state.status === "success") {
      toast.success(state.title, message);
    } else {
      toast.error(state.title, message);
    }
  }, [state, toast]);
}
