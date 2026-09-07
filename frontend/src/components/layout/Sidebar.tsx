import type { NavGroup } from "@/config/navigation";

import SidebarGroup from "./SidebarGroup";

interface SidebarProps {
  navigation: readonly NavGroup[];
  pathname: string;
  idPrefix: string;
  onNavigate?: () => void;
}

export default function Sidebar({
  navigation,
  pathname,
  idPrefix,
  onNavigate,
}: SidebarProps) {
  return (
    <nav aria-label="Primary navigation" className="space-y-6 p-3">
      {navigation.map((group) => (
        <SidebarGroup
          key={group.label}
          group={group}
          pathname={pathname}
          idPrefix={idPrefix}
          onNavigate={onNavigate}
        />
      ))}
    </nav>
  );
}
