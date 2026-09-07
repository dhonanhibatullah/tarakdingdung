"use server";

import { revalidatePath } from "next/cache";

import {
  createUser,
  deleteUser,
  resetUserPassword,
  updateUser,
} from "@/lib/api/users";
import { formText, optionalString } from "@/lib/forms/parse";
import {
  denied,
  fail,
  invalid,
  ok,
  type ActionResult,
} from "@/lib/forms/result";
import { requireSessionContext } from "@/lib/session";

export async function createUserAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("user:add")) {
    return denied();
  }

  const roleId = formText(formData, "role_id");
  const name = formText(formData, "name");
  const username = formText(formData, "username");
  const password = formText(formData, "password");

  if (!roleId) return invalid("Choose a role.");
  if (!name) return invalid("A name is required.");
  if (!username) return invalid("A username is required.");
  if (password.length < 8) {
    return invalid("The password must be at least 8 characters.");
  }

  try {
    await createUser({
      role_id: roleId,
      name,
      username,
      password,
      bio: optionalString(formData, "bio"),
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath("/admin/users");
  return ok("User created", `${username} can now sign in.`);
}

export async function updateUserAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("user:set")) {
    return denied();
  }

  const id = formText(formData, "id");
  if (!id) return invalid("Refresh and retry.");

  try {
    await updateUser(id, {
      role_id: optionalString(formData, "role_id"),
      name: optionalString(formData, "name"),
      bio: optionalString(formData, "bio"),
      username: optionalString(formData, "username"),
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath("/admin/users");
  return ok("User updated", "The changes have been saved.");
}

export async function resetPasswordAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("user_password:set")) {
    return denied();
  }

  const id = formText(formData, "id");
  const password = formText(formData, "password");
  if (!id) return invalid("Refresh and retry.");
  if (password.length < 8) {
    return invalid("The password must be at least 8 characters.");
  }

  try {
    await resetUserPassword(id, password);
  } catch (error) {
    return fail(error);
  }
  return ok("Password reset", "The user must sign in again with the new password.");
}

export async function deleteUserAction(
  _prev: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const session = await requireSessionContext();
  if (!session.permissions.has("user:remove")) {
    return denied();
  }

  const id = formText(formData, "id");
  const username = formText(formData, "username");
  const confirmation = formText(formData, "confirmation");
  if (!id || !username) return invalid("Refresh and retry.");
  if (confirmation !== username) {
    return invalid(`Type "${username}" exactly to confirm.`);
  }

  try {
    await deleteUser(id);
  } catch (error) {
    return fail(error);
  }
  revalidatePath("/admin/users");
  return ok("User deleted", `${username} has been removed.`);
}
