import ResourceCard from "@/components/collection/ResourceCard";
import type { PermissionResponse } from "@/lib/api/permissions";

import PermissionActions from "./PermissionActions";

interface PermissionCardProps {
  permission: PermissionResponse;
  sessionPermissions: ReadonlySet<string>;
}

export default function PermissionCard({
  permission,
  sessionPermissions,
}: PermissionCardProps) {
  return (
    <ResourceCard title={permission.name}>
      <p className="text-foreground/70">
        {permission.description || "No description."}
      </p>
      <div className="mt-5">
        <PermissionActions
          id={permission.id}
          name={permission.name}
          description={permission.description}
          canSet={sessionPermissions.has("permission:set")}
          canRemove={sessionPermissions.has("permission:remove")}
        />
      </div>
    </ResourceCard>
  );
}
