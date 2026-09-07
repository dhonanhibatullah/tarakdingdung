"use client";

import { CircleCheck, CircleX, X } from "lucide-react";
import { useEffect, useState } from "react";

export type ToastVariant = "success" | "error";

interface ToastProps {
  variant: ToastVariant;
  title: string;
  message: string;
  leaving: boolean;
  onClose: () => void;
}

const DURATION_MS = 3000;

const VARIANT_STYLES: Record<
  ToastVariant,
  { icon: typeof CircleCheck; iconClass: string; barClass: string }
> = {
  success: { icon: CircleCheck, iconClass: "text-success", barClass: "bg-success" },
  error: { icon: CircleX, iconClass: "text-critical", barClass: "bg-critical" },
};

export default function Toast({
  variant,
  title,
  message,
  leaving,
  onClose,
}: ToastProps) {
  const [entered, setEntered] = useState(false);
  const [barFilled, setBarFilled] = useState(false);

  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      setEntered(true);
      setBarFilled(true);
    });
    return () => cancelAnimationFrame(raf);
  }, []);

  const { icon: Icon, iconClass, barClass } = VARIANT_STYLES[variant];
  const visible = entered && !leaving;

  return (
    <div
      role="alert"
      data-toast
      className={`border-border bg-background pointer-events-auto relative w-full max-w-sm overflow-hidden rounded-2xl border shadow-lg transition-all duration-300 ease-out ${
        visible ? "translate-y-0 opacity-100" : "-translate-y-4 opacity-0"
      }`}
    >
      <div className="flex items-start gap-3 p-4 pr-10">
        <Icon className={`mt-0.5 size-5 shrink-0 ${iconClass}`} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-display text-foreground text-base tracking-wide">
            {title}
          </p>
          {message ? (
            <p className="text-foreground/70 mt-0.5 text-sm">{message}</p>
          ) : null}
        </div>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Dismiss notification"
        className="text-foreground/50 hover:bg-muted hover:text-foreground focus-visible:ring-focus absolute top-2 right-2 rounded-full p-1.5 transition-colors focus-visible:ring-2 focus-visible:outline-none"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
      <div className="bg-muted h-1 w-full">
        <div
          className={`h-full ${barClass} transition-[width] ease-linear`}
          style={{
            width: barFilled ? "100%" : "0%",
            transitionDuration: `${DURATION_MS}ms`,
          }}
        />
      </div>
    </div>
  );
}
