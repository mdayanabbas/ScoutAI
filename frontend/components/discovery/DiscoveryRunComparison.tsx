"use client";

import { sourceLabels } from "@/components/discovery/DiscoverySourceSelector";
import { StatusBadge, formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import type { DiscoveryRunListItem } from "@/types/discovery";

const comparisonFields = [
  ["provider_records_seen", "Provider Records"],
  ["candidates_created", "Candidates Created"],
  ["candidates_rejected", "Candidates Rejected"],
  ["domains_resolved", "Domains Resolved"],
  ["domains_unresolved", "Domains Unresolved"],
  ["jobs_created", "Jobs Created"],
  ["jobs_existing", "Jobs Existing"],
  ["jobs_enriched", "Jobs Enriched"],
  ["jobs_scored", "Jobs Scored"],
  ["jobs_failed", "Jobs Failed"],
  ["warnings", "Warnings"],
] as const;

export function DiscoveryRunComparison({
  runs,
  onClear,
}: {
  runs: DiscoveryRunListItem[];
  onClear: () => void;
}) {
  if (runs.length < 2) return null;

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Compare Runs</h2>
          <p className="mt-1 text-sm text-[#667085]">
            Comparing {runs.length} selected discovery runs.
          </p>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="self-start rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          Clear Compare
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
            <tr>
              <th className="py-2 pr-4 font-semibold">Run</th>
              <th className="py-2 pr-4 font-semibold">Source</th>
              <th className="py-2 pr-4 font-semibold">Status</th>
              <th className="py-2 pr-4 font-semibold">Duration</th>
              {comparisonFields.map(([, label]) => (
                <th key={label} className="py-2 pr-4 font-semibold">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((run, index) => {
              const id = runId(run) ?? `run-${index}`;
              const source = stringValue(run.source) ?? "unknown";
              return (
                <tr key={id} className="border-b border-[#f2f4f7] last:border-0">
                  <td className="max-w-44 truncate py-2 pr-4 font-mono text-xs text-[#475467]">
                    {id}
                  </td>
                  <td className="py-2 pr-4 font-medium text-[#171923]">
                    {sourceLabels[source] ?? source}
                  </td>
                  <td className="py-2 pr-4"><StatusBadge status={run.status} /></td>
                  <td className="py-2 pr-4 text-[#475467]">{formatRunDuration(run)}</td>
                  {comparisonFields.map(([key]) => (
                    <td key={key} className="py-2 pr-4 text-[#475467]">
                      {comparisonValue(run, key)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function comparisonValue(run: DiscoveryRunListItem, key: string) {
  if (key === "warnings") {
    if (Array.isArray(run.warnings)) return run.warnings.length;
    return numberValue(run.warning_count) ?? numberValue(run.warnings_count) ?? "-";
  }
  return numberValue(run[key]) ?? "-";
}

function formatRunDuration(run: DiscoveryRunListItem) {
  const explicit = numberValue(run.duration_ms);
  if (explicit !== null) return formatDuration(explicit);

  const started = dateMs(run.started_at);
  const finished = dateMs(run.finished_at);
  if (started === null || finished === null || finished < started) return "-";
  return formatDuration(finished - started);
}

function runId(run: DiscoveryRunListItem) {
  return stringValue(run.id) ?? stringValue(run.discovery_run_id);
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function dateMs(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? null : parsed;
}
