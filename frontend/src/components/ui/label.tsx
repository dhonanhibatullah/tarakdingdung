import type { LabelHTMLAttributes } from "react";

export default function Label({
  className = "",
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={`text-foreground/80 mb-1.5 block text-sm font-medium ${className}`}
      {...props}
    />
  );
}
