"use client";

import { Plus } from "lucide-react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import { useDialogForm } from "@/hooks/use-dialog-form";

import { createPermissionAction } from "../_lib/actions";

export default function NewPermissionDialog() {
  const { formAction, pending, dialogRef } = useDialogForm(
    createPermissionAction,
  );

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        <Plus aria-hidden="true" className="mr-1.5 size-4" />
        New permission
      </Button>

      <Modal dialogRef={dialogRef} title="New permission">
        <form action={formAction} className="space-y-4">
          <div>
            <Label htmlFor="np-name">Name</Label>
            <Input
              id="np-name"
              name="name"
              required
              autoComplete="off"
              placeholder="resource:action, e.g. strategy:get"
            />
          </div>
          <div>
            <Label htmlFor="np-description">Description (optional)</Label>
            <Input id="np-description" name="description" autoComplete="off" />
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
              {pending ? "Creating…" : "Create permission"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
