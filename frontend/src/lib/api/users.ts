import type { AuditFields } from "@/lib/api/types";

export interface UserResponse extends AuditFields {
  id: string;
  role_id: string;
  role_name?: string | null;
  name: string;
  bio: string;
  username: string;
  preferences: Record<string, unknown>;
}
