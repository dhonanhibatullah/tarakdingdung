import type { ReactNode, RefObject } from "react";

interface ModalProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  title: string;
  children: ReactNode;
  width?: string;
}

/** A native <dialog> shell. Callers own the <form> and the open/close calls. */
export default function Modal({
  dialogRef,
  title,
  children,
  width = "32rem",
}: ModalProps) {
  return (
    <dialog
      ref={dialogRef}
      style={{ width: `min(${width}, 94vw)` }}
      className="bg-background text-foreground m-auto rounded-2xl border border-[var(--border)] p-0 backdrop:bg-black/40"
    >
      <div className="max-h-[85vh] overflow-y-auto p-6">
        <h2 className="font-display text-primary mb-4 text-xl tracking-wide">
          {title}
        </h2>
        {children}
      </div>
    </dialog>
  );
}
