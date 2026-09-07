"use server";

import { revalidatePath } from "next/cache";

import {
  createPermission,
  deletePermission,
  updatePermission,
} from "@/lib/api/permissions";
import {
  assignRolePermission,
  createRole,
  deleteRole,
  getRolePermissions,
  revokeRolePermission,
  setDefaultRole,
  updateRole,
} from "@/lib/api/roles";
import { formText, optionalString } from "@/lib/forms/parse";
import {
  denied,
  fail,
  invalid,
  ok,
  type ActionResult,
} from "@/lib/forms/result";
import { requireSessionContext } from "@/lib/session";

const PATH = "/admin/access-control";

// ---- Roles ---------------------------------------------------------------

export async function createRoleAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("role:add")) return denied();
  const name = formText(formData, "name");
  if (!name) return invalid("A name is required.");
  try {
    await createRole({ name, description: optionalString(formData, "description") });
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Role created", `${name} is ready to receive permissions.`);
}

export async function updateRoleAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("role:set")) return denied();
  const id = formText(formData, "id");
  const name = formText(formData, "name");
  if (!id || !name) return invalid("A name is required.");
  try {
    await updateRole(id, {
      name,
      description: optionalString(formData, "description"),
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Role updated", "The changes have been saved.");
}

export async function setDefaultRoleAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("role:set")) return denied();
  const id = formText(formData, "id");
  if (!id) return invalid("Refresh and retry.");
  try {
    await setDefaultRole(id);
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Default role set", "New sign-ups will receive this role.");
}

export async function deleteRoleAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("role:remove")) return denied();
  const id = formText(formData, "id");
  const name = formText(formData, "name");
  if (!id || !name) return invalid("Refresh and retry.");
  if (formText(formData, "confirmation") !== name) {
    return invalid(`Type "${name}" exactly to confirm.`);
  }
  try {
    await deleteRole(id);
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Role deleted", `${name} has been removed.`);
}

export async function saveRolePermissionsAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (
    !session.permissions.has("role_permission:add") ||
    !session.permissions.has("role_permission:remove")
  ) {
    return denied();
  }
  const roleId = formText(formData, "role_id");
  if (!roleId) return invalid("Refresh and retry.");

  const selected = new Set(
    formData.getAll("permission_ids").map((v) => String(v)),
  );

  try {
    const current = await getRolePermissions(roleId);
    const currentIds = new Set(current.map((p) => p.id));
    const toAdd = [...selected].filter((id) => !currentIds.has(id));
    const toRemove = [...currentIds].filter((id) => !selected.has(id));

    for (const id of toAdd) {
      await assignRolePermission(roleId, id);
    }
    for (const id of toRemove) {
      await revokeRolePermission(roleId, id);
    }
    revalidatePath(PATH);
    return ok(
      "Permissions saved",
      `${toAdd.length} added, ${toRemove.length} removed.`,
    );
  } catch (error) {
    return fail(error);
  }
}

/** Read the ids a role currently holds — for prefilling the checkbox list. */
export async function loadRolePermissionIds(
  roleId: string,
): Promise<{ ok: true; ids: string[] } | { ok: false; message: string }> {
  const session = await requireSessionContext();
  if (!session.permissions.has("role_permission:get")) {
    return { ok: false, message: "Your account cannot view role permissions." };
  }
  try {
    const items = await getRolePermissions(roleId);
    return { ok: true, ids: items.map((p) => p.id) };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Could not load permissions.";
    return { ok: false, message };
  }
}

// ---- Permissions -------------------------------------------------------

export async function createPermissionAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("permission:add")) return denied();
  const name = formText(formData, "name");
  if (!name) return invalid("A name is required, e.g. strategy:get.");
  try {
    await createPermission({
      name,
      description: optionalString(formData, "description"),
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Permission created", `${name} can now be assigned to roles.`);
}

export async function updatePermissionAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("permission:set")) return denied();
  const id = formText(formData, "id");
  const name = formText(formData, "name");
  if (!id || !name) return invalid("A name is required.");
  try {
    await updatePermission(id, {
      name,
      description: optionalString(formData, "description"),
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Permission updated", "The changes have been saved.");
}

export async function deletePermissionAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("permission:remove")) return denied();
  const id = formText(formData, "id");
  const name = formText(formData, "name");
  if (!id || !name) return invalid("Refresh and retry.");
  if (formText(formData, "confirmation") !== name) {
    return invalid(`Type "${name}" exactly to confirm.`);
  }
  try {
    await deletePermission(id);
  } catch (error) {
    return fail(error);
  }
  revalidatePath(PATH);
  return ok("Permission deleted", `${name} has been removed.`);
}
