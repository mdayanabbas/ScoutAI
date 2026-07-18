"use client";

import Link from "next/link";

import { DiscoverySourceResultCard } from "@/components/discovery/DiscoverySourceResultCard";
import { StatusBadge, formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import {
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  normalizeExternalUrl,
} from "@/components/recommendations/recommendation-format";
import type {
  RemoteDiscoverySourceResult,
  RemoteDiscoveryTopRecommendation,
  RemoteJobDiscoveryOrchestratorResult,
} from "@/types/discovery";

export function DailyScoutRunResult({
  result,
  recentRunsCount,
  onOpenSourceDetails,
}: {
  result: RemoteJobDiscoveryOrchestratorResult;
  recentRunsCount: number;
  onOpenSourceDetails: (sourceResult: RemoteDiscoverySourceResult) => void;
}) {
  const sourceResults = result.source_results ?? [];
  const warnings = result.warnings ?? [];

  return (
    <div className="space-y-5">
      <section className="rounded-md border border-[#d9dee8] bg-white p-5">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#171923]">Daily Scout Run Summary</h2>
            <p className="mt-1 text-sm text-[#667085]">
              {dailyStatusMessage(result.status)}
            </p>
          </div>
          <StatusBadge status={result.status} />
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Duration" value={formatDuration(result.duration_ms)} />
          <Metric label="Sources planned" value={(result.sources_planned ?? []).join(", ") || "—"} />
          <Metric label="Sources completed" value={result.sources_completed ?? 0} />
          <Metric label="Sources failed" value={result.sources_failed ?? 0} />
          <Metric label="Sources skipped" value={result.sources_skipped ?? 0} />
          <Metric label="Provider records" value={result.total_provider_records_seen ?? 0} />
          <Metric label="Candidates created" value={result.total_candidates_created ?? 0} />
          <Metric label="Jobs created" value={result.total_jobs_created ?? 0} />
          <Metric label="Jobs existing" value={result.total_jobs_existing ?? 0} />
          <Metric label="Jobs enriched" value={sumSourceMetric(sourceResults, "jobs_enriched")} />
          <Metric label="Jobs scored" value={result.total_jobs_scored ?? 0} />
          <Metric label="Jobs failed" value={result.total_jobs_failed ?? 0} />
        </div>

        {warnings.length ? (
          <div className="mt-4 rounded border border-[#fedf89] bg-[#fffbeb] p-3 text-sm text-[#92400e]">
            <p className="font-semibold">Warnings</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {warnings.map((warning, index) => (
                <li key={`${warning}-${index}`}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <WhatChangedToday result={result} recentRunsCount={recentRunsCount} />

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-[#171923]">Daily Source Diagnostics</h2>
        {sourceResults.length ? (
          sourceResults.map((source, index) => (
            <DiscoverySourceResultCard
              key={`${source.source ?? "source"}-${index}`}
              result={source}
              onOpenDetails={onOpenSourceDetails}
            />
          ))
        ) : (
          <div className="rounded-md border border-[#d9dee8] bg-white p-5 text-sm text-[#667085]">
            No source-level diagnostics returned.
          </div>
        )}
      </section>

      <DailyScoutRecommendationQueue recommendations={result.top_recommendations ?? []} />
    </div>
  );
}

export function DailyScoutRecommendationQueue({
  recommendations,
}: {
  recommendations: RemoteDiscoveryTopRecommendation[];
}) {
  const groups = [
    ["Best matches", recommendations.filter((job) => isBestMatch(job))],
    ["Worth checking", recommendations.filter((job) => isWorthChecking(job))],
    ["Stretch", recommendations.filter((job) => String(job.match_tier ?? "").toLowerCase() === "stretch")],
  ] as const;

  if (!recommendations.length) {
    return (
      <section className="rounded-md border border-[#d9dee8] bg-white p-5">
        <h2 className="text-base font-semibold text-[#171923]">Daily Recommendation Queue</h2>
        <p className="mt-2 text-sm text-[#667085]">
          No recommendations returned from this run. Check source diagnostics to see whether jobs were fetched, enriched, scored, or filtered out.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <h2 className="text-base font-semibold text-[#171923]">Daily Recommendation Queue</h2>
      <div className="mt-4 space-y-5">
        {groups.map(([title, jobs]) =>
          jobs.length ? (
            <div key={title}>
              <h3 className="text-sm font-semibold text-[#344054]">{title}</h3>
              <div className="mt-3 space-y-3">
                {jobs.map((job, index) => (
                  <RecommendationCard key={job.job_id ?? `${title}-${index}`} job={job} />
                ))}
              </div>
            </div>
          ) : null,
        )}
      </div>
    </section>
  );
}

function RecommendationCard({ job }: { job: RemoteDiscoveryTopRecommendation }) {
  const jobId = job.job_id ?? "";
  const external = normalizeExternalUrl(job.apply_url) ?? normalizeExternalUrl(job.job_url);
  const salary = formatSalary({
    salary_min: job.salary_min,
    salary_max: job.salary_max,
    salary_currency: job.salary_currency,
  });

  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h4 className="text-base font-semibold text-[#171923]">{job.title ?? "Untitled job"}</h4>
          <p className="mt-1 text-sm text-[#667085]">{job.company_name ?? "Unknown company"}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-[#475467]">
            <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">Score {job.total_score ?? 0}</span>
            <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{job.eligibility_status ?? "unknown"}</span>
            <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{formatMatchTier(job.match_tier ?? "unknown")}</span>
            <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{formatRemoteEligibility(job.remote_eligibility ?? "unknown")}</span>
            {salary ? <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{salary}</span> : null}
          </div>
          {job.eligibility_reason ? <p className="mt-3 text-sm leading-6 text-[#344054]">{job.eligibility_reason}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {jobId ? (
            <Link href={`/jobs/${jobId}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
              Open Workspace
            </Link>
          ) : null}
          {external ? (
            <a href={external} target="_blank" rel="noopener noreferrer" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Open Job
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function WhatChangedToday({
  result,
  recentRunsCount,
}: {
  result: RemoteJobDiscoveryOrchestratorResult;
  recentRunsCount: number;
}) {
  const sourceResults = result.source_results ?? [];
  const sourcesWithWarnings = sourceResults
    .filter((source) => source.warnings?.length || source.error || source.status === "failed" || source.status === "partial")
    .map((source) => source.source ?? "unknown");

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <h2 className="text-base font-semibold text-[#171923]">What changed today?</h2>
      {recentRunsCount < 2 ? (
        <p className="mt-2 text-sm text-[#667085]">
          Run completed. Detailed comparison requires more run history.
        </p>
      ) : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="New jobs created" value={result.total_jobs_created ?? "—"} />
        <Metric label="Existing jobs refreshed" value={result.total_jobs_existing ?? "—"} />
        <Metric label="Jobs scored" value={result.total_jobs_scored ?? "—"} />
        <Metric label="Sources with warnings" value={sourcesWithWarnings.length} />
        <Metric label="Sources needing attention" value={sourcesWithWarnings.join(", ") || "—"} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
      <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-[#171923]">{value}</p>
    </div>
  );
}

function dailyStatusMessage(status?: string | null) {
  if (status === "failed") return "Daily Scout run failed. Check source-level errors below.";
  if (status === "partial") return "Daily Scout completed with warnings. Some sources may have failed or returned partial results.";
  return "Daily Scout finished. Review diagnostics and recommendations below.";
}

function isBestMatch(job: RemoteDiscoveryTopRecommendation) {
  const tier = String(job.match_tier ?? "").toLowerCase();
  const eligibility = String(job.eligibility_status ?? "").toLowerCase();
  return tier === "best_match" || tier === "best" || eligibility === "eligible";
}

function isWorthChecking(job: RemoteDiscoveryTopRecommendation) {
  const tier = String(job.match_tier ?? "").toLowerCase();
  return !isBestMatch(job) && tier !== "stretch" && !["unsuitable", "reject"].includes(tier);
}

function sumSourceMetric(sourceResults: Array<Record<string, unknown>>, key: string) {
  return sourceResults.reduce((sum, source) => {
    const value = source[key];
    return sum + (typeof value === "number" && Number.isFinite(value) ? value : 0);
  }, 0);
}
