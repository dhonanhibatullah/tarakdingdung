import FilterBar from "@/components/collection/FilterBar";
import Input from "@/components/ui/input";
import Select from "@/components/ui/select";

interface StrategyFiltersProps {
  search?: string;
  mode?: string;
}

export default function StrategyFilters({ search, mode }: StrategyFiltersProps) {
  return (
    <FilterBar clearHref="/strategies">
      <label>
        <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
          Search
        </span>
        <Input
          name="search"
          defaultValue={search}
          placeholder="Name"
          aria-label="Search strategies by name"
        />
      </label>
      <label>
        <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
          Mode
        </span>
        <Select name="mode" defaultValue={mode ?? ""} aria-label="Filter by mode">
          <option value="">Any mode</option>
          <option value="PAPER">Paper</option>
          <option value="LIVE">Live</option>
        </Select>
      </label>
    </FilterBar>
  );
}
