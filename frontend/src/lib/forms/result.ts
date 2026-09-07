// Import-free on purpose: client components pull INITIAL / ActionResult from
// here, so nothing server-only may leak in through this module.

/** The state shape every server action in the (app) pages returns. */
export interface ActionResult {
  status: "idle" | "success" | "error";
  title?: string;
  message?: string;
}

export const INITIAL: ActionResult = { status: "idle" };

export function ok(title: string, message: string): ActionResult {
  return { status: "success", title, message };
}

export function fail(error: unknown): ActionResult {
  // Duck-typed against ApiError (name + title) to avoid importing the
  // server-only api client into a module that client code also uses.
  if (
    error instanceof Error &&
    error.name === "ApiError" &&
    "title" in error &&
    typeof (error as { title: unknown }).title === "string"
  ) {
    return {
      status: "error",
      title: (error as { title: string }).title,
      message: error.message,
    };
  }
  return {
    status: "error",
    title: "Something went wrong",
    message: "The request could not be completed. Try again.",
  };
}

export function invalid(message: string): ActionResult {
  return { status: "error", title: "Check the form", message };
}

export function denied(): ActionResult {
  return {
    status: "error",
    title: "Permission denied",
    message: "Your account cannot make this change.",
  };
}
