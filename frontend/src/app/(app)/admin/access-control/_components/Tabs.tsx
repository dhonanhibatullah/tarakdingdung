import Link from "next/link";

interface TabsProps {
  active: "roles" | "permissions";
  showPermissions: boolean;
}

export default function Tabs({ active, showPermissions }: TabsProps) {
  const tabs: { key: "roles" | "permissions"; label: string }[] = [
    { key: "roles", label: "Roles" },
  ];
  if (showPermissions) {
    tabs.push({ key: "permissions", label: "Permissions" });
  }

  return (
    <nav className="border-border flex gap-1 border-b" aria-label="Access control sections">
      {tabs.map((tab) => {
        const current = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={`/admin/access-control?tab=${tab.key}`}
            aria-current={current ? "page" : undefined}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold ${
              current
                ? "border-primary text-primary"
                : "text-muted-foreground hover:text-foreground border-transparent"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
