import Link from "next/link";

interface WindowFilterProps {
  days: number;
  options: number[];
}

export default function WindowFilter({ days, options }: WindowFilterProps) {
  return (
    <div
      role="group"
      aria-label="Equity window"
      className="border-border inline-flex overflow-hidden rounded-xl border text-xs font-semibold"
    >
      {options.map((option) => {
        const active = option === days;
        return (
          <Link
            key={option}
            href={`/portfolio?days=${option}`}
            aria-current={active ? "true" : undefined}
            className={`px-3 py-2 ${
              active
                ? "bg-primary text-surface"
                : "text-primary hover:bg-highlight/40"
            }`}
          >
            {option}d
          </Link>
        );
      })}
    </div>
  );
}
