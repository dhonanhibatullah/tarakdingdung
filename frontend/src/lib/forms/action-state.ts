export type ActionState<TFields extends string = never> = {
  status: "idle" | "error" | "success";
  title?: string;
  message?: string;
  fieldErrors?: Partial<Record<TFields, string>>;
};

export const INITIAL_ACTION_STATE = { status: "idle" } as const;
