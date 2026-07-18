"use client";

import type { RemoteJobDiscoveryOrchestratorResult } from "@/types/discovery";

export function DiscoveryRunSummary({
  result,
}: {
  result: RemoteJobDiscoveryOrchestratorResult;
}) {
  const metrics = [
    ["Status", result.status ?? "unknown"],
    ["Sources", `${result.sources_completed ?? 0} completed / ${result.sources_failed ?? 0} failed / ${result.sources_skipped ?? 0} skipped`],
    ["Provider records", result.total_provider_records_seen ?? 0],
    ["Candidates created", result.total_candidates_created ?? 0],
    ["Candidates rejected", result.total_candidates_rejected ?? 0],
    ["Jobs created", result.total_jobs_created ?? 0],
    ["Jobs existing", result.total_jobs_existing ?? 0],
    ["Jobs updated", result.total_jobs_updated ?? 0],
    ["Jobs scored", result.total_jobs_scored ?? 0],
    ["Jobs failed", result.total_jobs_failed ?? 0],
    ["Duration", formatDuration(result.duration_ms)],
    ["Recommendation scope", result.recommendation_scope ?? "global"],
  ];

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Run Summary</h2>
          {result.reason ? (
            <p className="mt-1 text-sm text-[#667085]">{result.reason}</p>
          ) : null}
        </div>
        <StatusBadge status={result.status} />
      </div>

      {result.status === "partial" ? (
        <div className="mb-4 rounded border border-[#fedf89] bg-[#fffbeb] px-3 py-2 text-sm text-[#92400e]">
          Partial run. Some sources completed with warnings or failed; inspect source diagnostics below.
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div key={label} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
            <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
            <p className="mt-1 text-lg font-semibold text-[#171923]">{String(value)}</p>
          </div>
        ))}
      </div>

      {result.recommendation_source_filter?.length ? (
        <p className="mt-3 text-sm text-[#667085]">
          Recommendations filtered to {result.recommendation_source_filter.join(", ")}
          {typeof result.recommendation_job_ids_count === "number"
            ? ` across ${result.recommendation_job_ids_count} run job IDs.`
            : "."}
        </p>
      ) : null}
    </section>
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  const value = status ?? "unknown";
  const tone =
    value === "succeeded"
      ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]"
      : value === "partial"
        ? "border-[#fedf89] bg-[#fffbeb] text-[#92400e]"
        : value === "failed"
          ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]"
          : "border-[#d9dee8] bg-[#f8fafc] text-[#475467]";
  return (
    <span className={`inline-flex rounded border px-2.5 py-1 text-xs font-semibold ${tone}`}>
      {value}
    </span>
  );
}

export function formatDuration(value?: number | null) {
  if (typeof value !== "number") return "0 ms";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}
