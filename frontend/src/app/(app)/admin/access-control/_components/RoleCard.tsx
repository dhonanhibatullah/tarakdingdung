import ResourceCard from "@/components/collection/ResourceCard";
import StatusBadge from "@/components/ui/status-badge";
import type { RoleResponse } from "@/lib/api/roles";

import RoleActions from "./RoleActions";

interface RoleCardProps {
  role: RoleResponse;
  permissions: { id: string; name: string; description: string }[];
  sessionPermissions: ReadonlySet<string>;
}

export default function RoleCard({
  role,
  permissions,
  sessionPermissions,
}: RoleCardProps) {
  return (
    <ResourceCard
      title={role.name}
      summary={
        role.is_default ? (
          <StatusBadge variant="info">Default for new users</StatusBadge>
        ) : undefined
      }
    >
      <p className="text-foreground/70">{role.description || "No description."}</p>

      <div className="mt-5">
        <RoleActions
          id={role.id}
          name={role.name}
          description={role.description}
          isDefault={role.is_default}
          permissions={permissions}
          canSet={sessionPermissions.has("role:set")}
          canRemove={sessionPermissions.has("role:remove")}
          canManagePermissions={
            permissions.length > 0 &&
            sessionPermissions.has("role_permission:get") &&
            sessionPermissions.has("role_permission:add") &&
            sessionPermissions.has("role_permission:remove")
          }
        />
      </div>
    </ResourceCard>
  );
}
