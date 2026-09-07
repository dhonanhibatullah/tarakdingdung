"use server";

import { redirect } from "next/navigation";

import { login } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

export interface LoginFormState {
  title?: string;
  message?: string;
  username?: string;
}

export async function loginAction(
  _prevState: LoginFormState,
  formData: FormData,
): Promise<LoginFormState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!username || !password) {
    return {
      title: "Missing details",
      message: "Enter your username and password.",
      username,
    };
  }

  try {
    await login({ username, password });
  } catch (error) {
    if (error instanceof ApiError) {
      return { title: error.title, message: error.message, username };
    }
    return {
      title: "Something went wrong",
      message: "Could not reach the backend. Try again.",
      username,
    };
  }

  redirect("/dashboard");
}
