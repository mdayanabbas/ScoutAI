"use client";

const tierFilters = [
  { label: "All recommended", value: "" },
  { label: "Best matches", value: "best_match" },
  { label: "Strong matches", value: "strong_match" },
  { label: "Worth checking", value: "worth_checking" },
  { label: "Stretch", value: "stretch" },
];

export function RecommendationFilters({
  matchTier,
  includeRemoteUnknown,
  includeUnsuitable,
  disabled = false,
  onMatchTierChange,
  onIncludeRemoteUnknownChange,
  onIncludeUnsuitableChange,
}: {
  matchTier: string;
  includeRemoteUnknown: boolean;
  includeUnsuitable: boolean;
  disabled?: boolean;
  onMatchTierChange: (value: string) => void;
  onIncludeRemoteUnknownChange: (value: boolean) => void;
  onIncludeUnsuitableChange: (value: boolean) => void;
}) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap gap-2">
          {tierFilters.map((filter) => {
            const active = matchTier === filter.value;
            return (
              <button
                key={filter.label}
                type="button"
                disabled={disabled}
                onClick={() => onMatchTierChange(filter.value)}
                className={[
                  "rounded border px-3 py-2 text-sm font-medium",
                  active
                    ? "border-[#172033] bg-[#172033] text-white"
                    : "border-[#c8ced8] bg-white text-[#344054] hover:bg-[#f8fafc]",
                  disabled ? "cursor-not-allowed opacity-60" : "",
                ].join(" ")}
              >
                {filter.label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input
              type="checkbox"
              checked={includeRemoteUnknown}
              disabled={disabled}
              onChange={(event) =>
                onIncludeRemoteUnknownChange(event.target.checked)
              }
              className="h-4 w-4 rounded border-[#c8ced8]"
            />
            Include remote-unknown jobs
          </label>

          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input
              type="checkbox"
              checked={includeUnsuitable}
              disabled={disabled}
              onChange={(event) => onIncludeUnsuitableChange(event.target.checked)}
              className="h-4 w-4 rounded border-[#c8ced8]"
            />
            Show unsuitable jobs
          </label>
        </div>
      </div>
    </section>
  );
}
