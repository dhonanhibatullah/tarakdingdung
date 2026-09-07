"use client";

import { KeyRound, Pencil, Trash2 } from "lucide-react";

import Button from "@/components/ui/button";
import IconButton from "@/components/ui/icon-button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import Select from "@/components/ui/select";
import { useDialogForm } from "@/hooks/use-dialog-form";

import {
  deleteUserAction,
  resetPasswordAction,
  updateUserAction,
} from "../_lib/actions";

interface UserActionsProps {
  id: string;
  username: string;
  name: string;
  bio: string;
  roleId: string;
  roles: { id: string; name: string }[];
  canSet: boolean;
  canResetPassword: boolean;
  canRemove: boolean;
}

export default function UserActions({
  id,
  username,
  name,
  bio,
  roleId,
  roles,
  canSet,
  canResetPassword,
  canRemove,
}: UserActionsProps) {
  const edit = useDialogForm(updateUserAction);
  const pwd = useDialogForm(resetPasswordAction);
  const del = useDialogForm(deleteUserAction);

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
          <Modal dialogRef={edit.dialogRef} title={`Edit ${username}`}>
            <form action={edit.formAction} className="space-y-4">
              <input type="hidden" name="id" value={id} />
              <div>
                <Label htmlFor={`eu-role-${id}`}>Role</Label>
                <Select
                  id={`eu-role-${id}`}
                  name="role_id"
                  defaultValue={roleId}
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor={`eu-name-${id}`}>Name</Label>
                <Input id={`eu-name-${id}`} name="name" defaultValue={name} />
              </div>
              <div>
                <Label htmlFor={`eu-username-${id}`}>Username</Label>
                <Input
                  id={`eu-username-${id}`}
                  name="username"
                  defaultValue={username}
                />
              </div>
              <div>
                <Label htmlFor={`eu-bio-${id}`}>Bio</Label>
                <Input id={`eu-bio-${id}`} name="bio" defaultValue={bio} />
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

      {canResetPassword ? (
        <>
          <IconButton
            aria-label={`Reset password for ${username}`}
            onClick={() => pwd.dialogRef.current?.showModal()}
          >
            <KeyRound aria-hidden="true" className="size-4" />
          </IconButton>
          <Modal dialogRef={pwd.dialogRef} title={`Reset ${username}'s password`}>
            <form action={pwd.formAction} className="space-y-4">
              <input type="hidden" name="id" value={id} />
              <div>
                <Label htmlFor={`pw-${id}`}>New password</Label>
                <Input
                  id={`pw-${id}`}
                  name="password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => pwd.dialogRef.current?.close()}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={pwd.pending}>
                  {pwd.pending ? "Resetting…" : "Reset password"}
                </Button>
              </div>
            </form>
          </Modal>
        </>
      ) : null}

      {canRemove ? (
        <>
          <IconButton
            aria-label={`Delete ${username}`}
            onClick={() => del.dialogRef.current?.showModal()}
            className="text-critical hover:bg-critical/10"
          >
            <Trash2 aria-hidden="true" className="size-4" />
          </IconButton>
          <Modal dialogRef={del.dialogRef} title="Delete user" width="28rem">
            <form action={del.formAction} className="space-y-4">
              <p className="text-foreground/70 text-sm">
                This removes <span className="font-semibold">{username}</span>.
                Type the username to confirm.
              </p>
              <input type="hidden" name="id" value={id} />
              <input type="hidden" name="username" value={username} />
              <div>
                <Label htmlFor={`du-${id}`}>Username</Label>
                <Input
                  id={`du-${id}`}
                  name="confirmation"
                  autoComplete="off"
                  placeholder={username}
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
