export interface ActionResult {
  status: "idle" | "success" | "error";
  title?: string;
  message?: string;
}

export const INITIAL: ActionResult = { status: "idle" };
