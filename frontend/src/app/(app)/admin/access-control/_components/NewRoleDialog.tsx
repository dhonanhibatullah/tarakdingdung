"use client";

import { Plus } from "lucide-react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import { useDialogForm } from "@/hooks/use-dialog-form";

import { createRoleAction } from "../_lib/actions";

export default function NewRoleDialog() {
  const { formAction, pending, dialogRef } = useDialogForm(createRoleAction);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        <Plus aria-hidden="true" className="mr-1.5 size-4" />
        New role
      </Button>

      <Modal dialogRef={dialogRef} title="New role">
        <form action={formAction} className="space-y-4">
          <div>
            <Label htmlFor="nr-name">Name</Label>
            <Input id="nr-name" name="name" required autoComplete="off" />
          </div>
          <div>
            <Label htmlFor="nr-description">Description (optional)</Label>
            <Input id="nr-description" name="description" autoComplete="off" />
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
              {pending ? "Creating…" : "Create role"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
