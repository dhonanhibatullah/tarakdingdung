import FilterBar from "@/components/collection/FilterBar";
import Input from "@/components/ui/input";
import Select from "@/components/ui/select";

interface BacktestFiltersProps {
  strategyId?: string;
  strategies: { id: string; name: string }[];
}

export default function BacktestFilters({
  strategyId,
  strategies,
}: BacktestFiltersProps) {
  return (
    <FilterBar clearHref="/backtests">
      <label>
        <span className="text-foreground/70 mb-1.5 block text-xs font-semibold">
          Strategy
        </span>
        {strategies.length > 0 ? (
          <Select
            name="strategy_id"
            defaultValue={strategyId ?? ""}
            aria-label="Filter by strategy"
          >
            <option value="">Any strategy</option>
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        ) : (
          <Input
            name="strategy_id"
            defaultValue={strategyId}
            placeholder="Strategy UUID"
            aria-label="Filter by strategy id"
          />
        )}
      </label>
    </FilterBar>
  );
}
