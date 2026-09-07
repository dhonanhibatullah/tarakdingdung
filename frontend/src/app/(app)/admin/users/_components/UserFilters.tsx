import FilterBar from "@/components/collection/FilterBar";
import Input from "@/components/ui/input";
import Select from "@/components/ui/select";

interface UserFiltersProps {
  search?: string;
  roleId?: string;
  roles: { id: string; name: string }[];
}

export default function UserFilters({
  search,
  roleId,
  roles,
}: UserFiltersProps) {
  return (
    <FilterBar clearHref="/admin/users">
      <label>
        <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
          Search
        </span>
        <Input
          name="search"
          defaultValue={search}
          placeholder="Name or username"
          aria-label="Search users"
        />
      </label>
      <label>
        <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
          Role
        </span>
        <Select
          name="role_id"
          defaultValue={roleId ?? ""}
          aria-label="Filter by role"
        >
          <option value="">Any role</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </Select>
      </label>
    </FilterBar>
  );
}
