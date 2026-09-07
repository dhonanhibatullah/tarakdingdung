"use client";

import { Eye, EyeOff } from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";

import { loginAction, type LoginFormState } from "../_lib/actions";

const initialState: LoginFormState = {};

export default function LoginForm() {
  const [state, formAction, isPending] = useActionState(
    loginAction,
    initialState,
  );
  const [showPassword, setShowPassword] = useState(false);
  const toast = useToast();
  const lastShown = useRef<LoginFormState | null>(null);

  useEffect(() => {
    if (state.title && state !== lastShown.current) {
      lastShown.current = state;
      toast.error(state.title, state.message ?? "");
    }
  }, [state, toast]);

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <div>
        <Label htmlFor="username">Username</Label>
        <Input
          id="username"
          name="username"
          autoComplete="username"
          placeholder="Enter your username"
          defaultValue={state.username}
          autoFocus
          required
        />
      </div>

      <div>
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="Enter your password"
            className="pr-10"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword((show) => !show)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="text-foreground/40 hover:text-foreground/70 absolute inset-y-0 right-0 flex items-center px-3"
          >
            {showPassword ? (
              <EyeOff aria-hidden="true" className="size-4" />
            ) : (
              <Eye aria-hidden="true" className="size-4" />
            )}
          </button>
        </div>
      </div>

      <Button type="submit" disabled={isPending} className="mt-1 w-full">
        {isPending ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
