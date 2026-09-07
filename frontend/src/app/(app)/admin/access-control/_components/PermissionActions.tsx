"use client";

import { Pencil, Trash2 } from "lucide-react";

import Button from "@/components/ui/button";
import IconButton from "@/components/ui/icon-button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import { useDialogForm } from "@/hooks/use-dialog-form";

import { deletePermissionAction, updatePermissionAction } from "../_lib/actions";

interface PermissionActionsProps {
  id: string;
  name: string;
  description: string;
  canSet: boolean;
  canRemove: boolean;
}

export default function PermissionActions({
  id,
  name,
  description,
  canSet,
  canRemove,
}: PermissionActionsProps) {
  const edit = useDialogForm(updatePermissionAction);
  const del = useDialogForm(deletePermissionAction);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canSet ? (
        <>
          <Button
            type="button"
            variant="secondary"
            onClick={() => edit.dialogRef.current?.showModal()}
          >
            <Pencil aria-hidden="true" className="mr-1.5 size-4" />
            Edit
          </Button>
          <Modal dialogRef={edit.dialogRef} title={`Edit ${name}`}>
            <form action={edit.formAction} className="space-y-4">
              <input type="hidden" name="id" value={id} />
              <div>
                <Label htmlFor={`ep-name-${id}`}>Name</Label>
                <Input
                  id={`ep-name-${id}`}
                  name="name"
                  defaultValue={name}
                  required
                />
              </div>
              <div>
                <Label htmlFor={`ep-desc-${id}`}>Description</Label>
                <Input
                  id={`ep-desc-${id}`}
                  name="description"
                  defaultValue={description}
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => edit.dialogRef.current?.close()}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={edit.pending}>
                  {edit.pending ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </form>
          </Modal>
        </>
      ) : null}

      {canRemove ? (
        <>
          <IconButton
            aria-label={`Delete ${name}`}
            onClick={() => del.dialogRef.current?.showModal()}
            className="text-critical hover:bg-critical/10"
          >
            <Trash2 aria-hidden="true" className="size-4" />
          </IconButton>
          <Modal dialogRef={del.dialogRef} title="Delete permission" width="28rem">
            <form action={del.formAction} className="space-y-4">
              <p className="text-foreground/70 text-sm">
                This removes <span className="font-semibold">{name}</span> from
                every role that holds it. Type its name to confirm.
              </p>
              <input type="hidden" name="id" value={id} />
              <input type="hidden" name="name" value={name} />
              <div>
                <Label htmlFor={`dp-${id}`}>Permission name</Label>
                <Input
                  id={`dp-${id}`}
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
                  onClick={() => del.dialogRef.current?.close()}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="critical" disabled={del.pending}>
                  {del.pending ? "Deleting…" : "Delete"}
                </Button>
              </div>
            </form>
          </Modal>
        </>
      ) : null}
    </div>
  );
}
