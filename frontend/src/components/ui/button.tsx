import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "critical" | "success";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-surface hover:opacity-90 active:opacity-80 disabled:opacity-50",
  secondary:
    "border border-border text-primary hover:bg-highlight/40 active:bg-highlight/60 disabled:opacity-50",
  critical:
    "border border-critical text-critical hover:bg-critical/10 active:bg-critical/15 disabled:opacity-50",
  success:
    "bg-success text-surface hover:opacity-90 active:opacity-80 disabled:opacity-50",
};

export default function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`focus-visible:ring-focus focus-visible:ring-offset-background inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
}
