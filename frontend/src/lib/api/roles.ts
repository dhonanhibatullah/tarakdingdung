import type { AuditFields } from "@/lib/api/types";

export interface RoleResponse extends AuditFields {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  preferences: Record<string, unknown>;
}
