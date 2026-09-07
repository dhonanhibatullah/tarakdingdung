"use client";

import { ShieldCheck } from "lucide-react";
import { useCallback, useState, useTransition } from "react";

import Button from "@/components/ui/button";
import Modal from "@/components/ui/modal";
import { useDialogForm } from "@/hooks/use-dialog-form";

import { loadRolePermissionIds, saveRolePermissionsAction } from "../_lib/actions";

interface RolePermissionsDialogProps {
  roleId: string;
  roleName: string;
  permissions: { id: string; name: string; description: string }[];
}

export default function RolePermissionsDialog({
  roleId,
  roleName,
  permissions,
}: RolePermissionsDialogProps) {
  const { formAction, pending, dialogRef } = useDialogForm(
    saveRolePermissionsAction,
  );
  const [assigned, setAssigned] = useState<Set<string> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, startLoading] = useTransition();

  const open = useCallback(() => {
    setAssigned(null);
    setLoadError(null);
    dialogRef.current?.showModal();
    startLoading(async () => {
      const result = await loadRolePermissionIds(roleId);
      if (result.ok) {
        setAssigned(new Set(result.ids));
      } else {
        setLoadError(result.message);
      }
    });
  }, [dialogRef, roleId]);

  return (
    <>
      <Button type="button" variant="secondary" onClick={open}>
        <ShieldCheck aria-hidden="true" className="mr-1.5 size-4" />
        Permissions
      </Button>

      <Modal
        dialogRef={dialogRef}
        title={`Permissions for ${roleName}`}
        width="40rem"
      >
        {loading || assigned === null ? (
          <p className="text-muted-foreground text-sm">
            {loadError ?? "Loading current permissions…"}
          </p>
        ) : (
          <form action={formAction} className="space-y-4">
            <input type="hidden" name="role_id" value={roleId} />
            <div className="border-border max-h-[50vh] space-y-1 overflow-y-auto rounded-xl border p-2">
              {permissions.map((permission) => (
                <label
                  key={permission.id}
                  className="hover:bg-muted flex items-start gap-3 rounded-lg p-2 text-sm"
                >
                  <input
                    type="checkbox"
                    name="permission_ids"
                    value={permission.id}
                    defaultChecked={assigned.has(permission.id)}
                    className="mt-0.5 size-4"
                  />
                  <span>
                    <span className="font-mono font-medium">
                      {permission.name}
                    </span>
                    {permission.description ? (
                      <span className="text-muted-foreground block text-xs">
                        {permission.description}
                      </span>
                    ) : null}
                  </span>
                </label>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => dialogRef.current?.close()}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={pending}>
                {pending ? "Saving…" : "Save permissions"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
