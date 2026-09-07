"use client";

import { Pencil, Star, Trash2 } from "lucide-react";

import Button from "@/components/ui/button";
import IconButton from "@/components/ui/icon-button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import { useDialogForm } from "@/hooks/use-dialog-form";

import {
  deleteRoleAction,
  setDefaultRoleAction,
  updateRoleAction,
} from "../_lib/actions";
import RolePermissionsDialog from "./RolePermissionsDialog";

interface RoleActionsProps {
  id: string;
  name: string;
  description: string;
  isDefault: boolean;
  permissions: { id: string; name: string; description: string }[];
  canSet: boolean;
  canRemove: boolean;
  canManagePermissions: boolean;
}

export default function RoleActions({
  id,
  name,
  description,
  isDefault,
  permissions,
  canSet,
  canRemove,
  canManagePermissions,
}: RoleActionsProps) {
  const edit = useDialogForm(updateRoleAction);
  const del = useDialogForm(deleteRoleAction);
  const setDefault = useDialogForm(setDefaultRoleAction);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canManagePermissions ? (
        <RolePermissionsDialog
          roleId={id}
          roleName={name}
          permissions={permissions}
        />
      ) : null}

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
                <Label htmlFor={`er-name-${id}`}>Name</Label>
                <Input id={`er-name-${id}`} name="name" defaultValue={name} required />
              </div>
              <div>
                <Label htmlFor={`er-desc-${id}`}>Description</Label>
                <Input
                  id={`er-desc-${id}`}
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

          {!isDefault ? (
            <form action={setDefault.formAction}>
              <input type="hidden" name="id" value={id} />
              <Button
                type="submit"
                variant="secondary"
                disabled={setDefault.pending}
              >
                <Star aria-hidden="true" className="mr-1.5 size-4" />
                Make default
              </Button>
            </form>
          ) : null}
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
          <Modal dialogRef={del.dialogRef} title="Delete role" width="28rem">
            <form action={del.formAction} className="space-y-4">
              <p className="text-foreground/70 text-sm">
                This removes <span className="font-semibold">{name}</span>. Type
                its name to confirm.
              </p>
              <input type="hidden" name="id" value={id} />
              <input type="hidden" name="name" value={name} />
              <div>
                <Label htmlFor={`dr-${id}`}>Role name</Label>
                <Input
                  id={`dr-${id}`}
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
