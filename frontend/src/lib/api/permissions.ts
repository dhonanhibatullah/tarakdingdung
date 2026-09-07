import type { AuditFields } from "@/lib/api/types";

export interface PermissionResponse extends AuditFields {
  id: string;
  name: string;
  description: string;
  preferences: Record<string, unknown>;
}
