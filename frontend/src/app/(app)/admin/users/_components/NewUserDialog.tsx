"use client";

import { Plus } from "lucide-react";

import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import Label from "@/components/ui/label";
import Modal from "@/components/ui/modal";
import Select from "@/components/ui/select";
import { useDialogForm } from "@/hooks/use-dialog-form";

import { createUserAction } from "../_lib/actions";

interface NewUserDialogProps {
  roles: { id: string; name: string }[];
}

export default function NewUserDialog({ roles }: NewUserDialogProps) {
  const { formAction, pending, dialogRef } = useDialogForm(createUserAction);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        <Plus aria-hidden="true" className="mr-1.5 size-4" />
        New user
      </Button>

      <Modal dialogRef={dialogRef} title="New user">
        <form action={formAction} className="space-y-4">
          <div>
            <Label htmlFor="nu-role">Role</Label>
            <Select id="nu-role" name="role_id" required defaultValue="">
              <option value="" disabled>
                Select a role…
              </option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="nu-name">Name</Label>
            <Input id="nu-name" name="name" required autoComplete="off" />
          </div>
          <div>
            <Label htmlFor="nu-username">Username</Label>
            <Input id="nu-username" name="username" required autoComplete="off" />
          </div>
          <div>
            <Label htmlFor="nu-password">Password</Label>
            <Input
              id="nu-password"
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
          <div>
            <Label htmlFor="nu-bio">Bio (optional)</Label>
            <Input id="nu-bio" name="bio" autoComplete="off" />
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
              {pending ? "Creating…" : "Create user"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
