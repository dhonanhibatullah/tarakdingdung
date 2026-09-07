import Link from "next/link";

interface VenueSelectProps {
  venues: string[];
  active: string;
  /** Preserved so switching venue keeps the equity-curve window. */
  days: number;
}

export default function VenueSelect({ venues, active, days }: VenueSelectProps) {
  if (venues.length < 2) {
    return null;
  }
  return (
    <div
      role="group"
      aria-label="Venue"
      className="border-border inline-flex overflow-hidden rounded-xl border text-xs font-semibold"
    >
      {venues.map((venue) => {
        const current = venue === active;
        return (
          <Link
            key={venue}
            href={`/portfolio?venue=${venue}&days=${days}`}
            aria-current={current ? "true" : undefined}
            className={`px-3 py-2 ${
              current
                ? "bg-primary text-surface"
                : "text-primary hover:bg-highlight/40"
            }`}
          >
            {venue}
          </Link>
        );
      })}
    </div>
  );
}
