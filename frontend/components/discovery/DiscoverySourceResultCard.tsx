"use client";

import { sourceLabels } from "@/components/discovery/DiscoverySourceSelector";
import { StatusBadge, formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import type { RemoteDiscoverySourceResult } from "@/types/discovery";

const discoveryMetrics = [
  "provider_records_seen",
  "unique_records",
  "candidates_found",
  "candidates_normalized",
  "candidates_created",
  "candidates_deferred",
  "candidates_rejected",
  "candidates_failed",
] as const;

const companyMetrics = [
  "companies_created",
  "companies_matched",
  "domains_resolved",
  "domains_unresolved",
] as const;

const jobMetrics = [
  "jobs_created",
  "jobs_existing",
  "jobs_updated",
  "jobs_skipped",
  "jobs_enriched",
  "jobs_scored",
  "jobs_failed",
] as const;

const hnMetrics = [
  "h_n_jobs_scored_eligible",
  "h_n_jobs_scored_stretch",
  "h_n_jobs_scored_uncertain",
  "h_n_jobs_scored_unsuitable",
  "h_n_jobs_remaining_open_roles",
  "h_n_jobs_remaining_remote_unknown",
  "h_n_jobs_not_enriched",
] as const;

export function DiscoverySourceResultCard({
  result,
  onOpenDetails,
}: {
  result: RemoteDiscoverySourceResult;
  onOpenDetails?: (result: RemoteDiscoverySourceResult) => void;
}) {
  const source = result.source ?? "unknown";
  const diagnostics = result.diagnostics ?? {};
  const jobIds = Array.isArray(diagnostics.job_ids) ? diagnostics.job_ids : [];

  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-[#171923]">
            {sourceLabels[source] ?? source}
          </h3>
          <p className="mt-1 text-sm text-[#667085]">
            {result.reason ?? "Source completed."}
            {result.discovery_run_id ? ` Run ${result.discovery_run_id}.` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={result.status} />
          <span className="rounded border border-[#e4e7ec] px-2.5 py-1 text-xs font-medium text-[#475467]">
            {formatDuration(result.duration_ms)}
          </span>
          {result.discovery_run_id && onOpenDetails ? (
            <button
              type="button"
              onClick={() => onOpenDetails(result)}
              className="rounded border border-[#c8ced8] px-2.5 py-1 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              View Details
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <MetricGroup title="Discovery" metrics={discoveryMetrics} result={result} />
        <MetricGroup title="Company / Domain" metrics={companyMetrics} result={result} />
        <MetricGroup title="Jobs" metrics={jobMetrics} result={result} />
      </div>

      {source === "hacker_news" ? (
        <div className="mt-4 rounded border border-[#dbeafe] bg-[#eff6ff] p-4">
          <h4 className="text-sm font-semibold text-[#1e3a8a]">Hacker News Diagnostics</h4>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {hnMetrics.map((key) => (
              <MiniMetric key={key} label={labelize(key)} value={diagnostics[key]} />
            ))}
          </div>
          {(result.jobs_skipped ?? 0) > 0 ? (
            <p className="mt-3 text-sm text-[#1d4ed8]">
              Some HN candidates did not become jobs because company/domain resolution was incomplete or the candidate was not actionable.
            </p>
          ) : null}
          {(result.jobs_enriched ?? 0) < (result.jobs_created ?? 0) + (result.jobs_existing ?? 0) ? (
            <p className="mt-2 text-sm text-[#1d4ed8]">
              Some HN jobs still need enrichment before they can rank well.
            </p>
          ) : null}
        </div>
      ) : null}

      {result.error ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">
          Source failed: {result.error}
        </div>
      ) : null}

      {result.warnings?.length ? (
        <div className="mt-4 rounded border border-[#fedf89] bg-[#fffbeb] px-3 py-2 text-sm text-[#92400e]">
          <p className="font-semibold">Source completed with warnings</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {result.warnings.map((warning, index) => (
              <li key={`${warning}-${index}`}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <details className="mt-4 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
        <summary className="cursor-pointer text-sm font-medium text-[#344054]">
          Diagnostics details
        </summary>
        <div className="mt-3 space-y-2 text-sm text-[#475467]">
          {Array.isArray(diagnostics.phases) ? (
            <p>Phases: {diagnostics.phases.join(" -> ")}</p>
          ) : null}
          <p>{jobIds.length} job IDs tracked</p>
          {jobIds.length ? (
            <pre className="max-h-28 overflow-auto rounded bg-[#101828] p-3 text-xs text-white">
              {jobIds.join("\n")}
            </pre>
          ) : null}
        </div>
      </details>
    </article>
  );
}

function MetricGroup({
  title,
  metrics,
  result,
}: {
  title: string;
  metrics: readonly string[];
  result: RemoteDiscoverySourceResult;
}) {
  return (
    <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
      <h4 className="text-sm font-semibold text-[#344054]">{title}</h4>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {metrics.map((key) => (
          <MiniMetric key={key} label={labelize(key)} value={result[key as keyof RemoteDiscoverySourceResult]} />
        ))}
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <p className="text-xs text-[#667085]">{label}</p>
      <p className="text-sm font-semibold text-[#171923]">{String(value ?? 0)}</p>
    </div>
  );
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
