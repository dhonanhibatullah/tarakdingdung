import ResourceCard from "@/components/collection/ResourceCard";
import StatusBadge from "@/components/ui/status-badge";
import type { UserResponse } from "@/lib/api/users";

import UserActions from "./UserActions";

interface UserCardProps {
  user: UserResponse;
  roles: { id: string; name: string }[];
  permissions: ReadonlySet<string>;
}

export default function UserCard({ user, roles, permissions }: UserCardProps) {
  const roleName =
    user.role_name ?? roles.find((r) => r.id === user.role_id)?.name ?? "—";

  return (
    <ResourceCard
      title={user.username}
      summary={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge variant="info">{roleName}</StatusBadge>
        </div>
      }
    >
      <dl className="space-y-2">
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">Name</dt>
          <dd className="text-right font-medium">{user.name || "—"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">Bio</dt>
          <dd className="min-w-0 text-right font-medium break-words">
            {user.bio || "—"}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <UserActions
          id={user.id}
          username={user.username}
          name={user.name}
          bio={user.bio}
          roleId={user.role_id}
          roles={roles}
          canSet={permissions.has("user:set")}
          canResetPassword={permissions.has("user_password:set")}
          canRemove={permissions.has("user:remove")}
        />
      </div>
    </ResourceCard>
  );
}
