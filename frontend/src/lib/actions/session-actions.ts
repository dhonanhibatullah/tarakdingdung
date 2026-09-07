"use server";

import { redirect } from "next/navigation";

import { logout } from "@/lib/api/auth";

export async function logoutAction(): Promise<void> {
  await logout();
  redirect("/login?signedOut=1");
}
