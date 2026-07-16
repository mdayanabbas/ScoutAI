"use client";

import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { RecommendedJobCard } from "@/components/recommendations/RecommendedJobCard";
import { RecommendationFilters } from "@/components/recommendations/RecommendationFilters";
import { generateApplicationPrepForJob } from "@/lib/application-prep-api";
import { useRecommendedJobMatches } from "@/hooks/use-job-matches";
import { runUnifiedRemoteDiscovery } from "@/lib/job-matches-api";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { JobApplicationDecisionResponse } from "@/types/job-decision";
import type {
  RecommendedJobMatch,
  RecommendedJobMatchParams,
  RemoteDiscoverySourceResult,
  RemoteJobDiscoveryOrchestratorResult,
} from "@/types/job-match";

export default function RecommendationsPage() {
  const [matchTier, setMatchTier] = useState("");
  const [includeRemoteUnknown, setIncludeRemoteUnknown] = useState(false);
  const [includeUnsuitable, setIncludeUnsuitable] = useState(false);
  const [discoveryResult, setDiscoveryResult] =
    useState<RemoteJobDiscoveryOrchestratorResult | null>(null);
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState<string | null>(null);
  const [prepByJobId, setPrepByJobId] = useState<Record<string, ApplicationPrepResponse>>({});
  const [prepErrors, setPrepErrors] = useState<Record<string, string>>({});
  const [prepPendingJobId, setPrepPendingJobId] = useState<string | null>(null);
  const [decisionByJobId, setDecisionByJobId] = useState<Record<string, JobApplicationDecisionResponse>>({});

  const params = useMemo<RecommendedJobMatchParams>(
    () => ({
      order_by: "recommended",
      limit: 50,
      include_remote_unknown: includeRemoteUnknown,
      include_unsuitable: includeUnsuitable,
      match_tier: matchTier || undefined,
    }),
    [includeRemoteUnknown, includeUnsuitable, matchTier],
  );
  const recommendationsQuery = useRecommendedJobMatches(params);
  const jobs = recommendationsQuery.data?.items ?? [];
  const stats = useMemo(() => summarize(jobs), [jobs]);

  async function findNewRemoteJobs() {
    setDiscoveryRunning(true);
    setDiscoveryMessage("Finding remote jobs...");
    setDiscoveryResult(null);

    try {
      const result = await runUnifiedRemoteDiscovery();
      setDiscoveryResult(result);
      await recommendationsQuery.refetch();
    } catch (error) {
      setDiscoveryResult({
        status: "failed",
        reason: error instanceof Error ? error.message : "Discovery failed",
        sources_planned: [],
        source_results: [],
      });
    } finally {
      setDiscoveryRunning(false);
      setDiscoveryMessage(null);
    }
  }

  async function prepareApplication(job: RecommendedJobMatch) {
    setPrepPendingJobId(job.job_id);
    setPrepErrors((current) => {
      const next = { ...current };
      delete next[job.job_id];
      return next;
    });

    try {
      const prep = await generateApplicationPrepForJob(job.job_id);
      setPrepByJobId((current) => ({ ...current, [job.job_id]: prep }));
      if (prep.decision_id) {
        setDecisionByJobId((current) => ({
          ...current,
          [job.job_id]: {
            id: prep.decision_id ?? "",
            job_id: job.job_id,
            decision_status:
              job.match_tier === "best_match" || job.match_tier === "strong_match"
                ? "needs_custom_resume"
                : "saved",
            status:
              job.match_tier === "best_match" || job.match_tier === "strong_match"
                ? "needs_custom_resume"
                : "saved",
            priority: job.match_tier === "best_match" ? "high" : "medium",
            fit_summary: prep.fit_summary,
            concerns: (prep.concerns ?? []).map((item) => item.value ?? "").filter(Boolean).join("\n"),
            next_action: prep.suggested_next_action,
          },
        }));
      }
    } catch (error) {
      setPrepErrors((current) => ({
        ...current,
        [job.job_id]:
          error instanceof Error ? error.message : "Could not prepare application notes.",
      }));
    } finally {
      setPrepPendingJobId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Recommended Jobs"
        description="AI/ML/FDE/SWE roles matched to your remote-from-India profile."
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => recommendationsQuery.refetch()}
              disabled={recommendationsQuery.isFetching || discoveryRunning}
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
            >
              Refresh recommendations
            </button>
            <button
              type="button"
              onClick={findNewRemoteJobs}
              disabled={discoveryRunning}
              className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {discoveryRunning ? "Finding remote jobs..." : "Find New Remote Jobs"}
            </button>
          </div>
        }
      />

      <SummaryStats
        total={recommendationsQuery.data?.total ?? jobs.length}
        best={stats.best}
        worthChecking={stats.worthChecking}
        stale={stats.stale}
      />

      <RecommendationFilters
        matchTier={matchTier}
        includeRemoteUnknown={includeRemoteUnknown}
        includeUnsuitable={includeUnsuitable}
        disabled={recommendationsQuery.isFetching || discoveryRunning}
        onMatchTierChange={setMatchTier}
        onIncludeRemoteUnknownChange={setIncludeRemoteUnknown}
        onIncludeUnsuitableChange={setIncludeUnsuitable}
      />

      {discoveryMessage ? (
        <div className="mb-5 rounded-md border border-[#bfdbfe] bg-[#eff6ff] p-4 text-sm font-medium text-[#1d4ed8]">
          {discoveryMessage}
        </div>
      ) : null}

      {discoveryResult ? (
        <DiscoverySummary result={discoveryResult} />
      ) : null}

      {recommendationsQuery.isLoading ? <LoadingState /> : null}

      {recommendationsQuery.error ? (
        <ErrorState
          message={
            recommendationsQuery.error instanceof Error
              ? recommendationsQuery.error.message
              : "Check the backend API."
          }
          onRetry={() => recommendationsQuery.refetch()}
        />
      ) : null}

      {!recommendationsQuery.isLoading &&
      !recommendationsQuery.error &&
      jobs.length === 0 ? (
        <EmptyState
          includeRemoteUnknown={includeRemoteUnknown}
          includeUnsuitable={includeUnsuitable}
          onFindNewRemoteJobs={findNewRemoteJobs}
          onIncludeRemoteUnknown={() => setIncludeRemoteUnknown(true)}
          onShowStretch={() => setMatchTier("stretch")}
        />
      ) : null}

      {!recommendationsQuery.error && jobs.length > 0 ? (
        <section className="space-y-4">
          {recommendationsQuery.isFetching && !recommendationsQuery.isLoading ? (
            <p className="text-sm text-[#667085]">Updating recommendations...</p>
          ) : null}
          {jobs.map((job) => (
            <RecommendedJobCard
              key={job.job_id}
              job={job}
              decision={decisionByJobId[job.job_id]}
              prep={prepByJobId[job.job_id]}
              prepPending={prepPendingJobId === job.job_id}
              prepError={prepErrors[job.job_id]}
              onPrepareApplication={prepareApplication}
            />
          ))}
        </section>
      ) : null}
    </>
  );
}

function SummaryStats({
  total,
  best,
  worthChecking,
  stale,
}: {
  total: number;
  best: number;
  worthChecking: number;
  stale: number;
}) {
  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Recommendations" value={total} />
      <Stat label="Best matches" value={best} />
      <Stat label="Worth checking" value={worthChecking} />
      <Stat label="Stale scores" value={stale} />
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-normal text-[#667085]">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-[#171923]">{value}</div>
    </div>
  );
}

function DiscoverySummary({
  result,
}: {
  result: RemoteJobDiscoveryOrchestratorResult;
}) {
  const tone = discoveryTone(result.status);
  const sourceResults = result.source_results ?? [];

  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#171923]">
            Discovery summary
          </h2>
          <p className={`mt-1 text-sm ${tone.textClass}`}>
            {discoverySummaryMessage(result)}
          </p>
          {result.reason ? (
            <p className="mt-1 text-xs text-[#667085]">{result.reason}</p>
          ) : null}
        </div>
        <span
          className={`w-fit rounded px-2 py-1 text-xs font-semibold uppercase tracking-normal ${tone.badgeClass}`}
        >
          {result.status}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
        <Stat label="Sources completed" value={result.sources_completed ?? 0} />
        <Stat label="Sources failed" value={result.sources_failed ?? 0} />
        <Stat label="New jobs" value={result.total_jobs_created ?? 0} />
        <Stat label="Existing jobs" value={result.total_jobs_existing ?? 0} />
        <Stat label="Updated jobs" value={result.total_jobs_updated ?? 0} />
        <Stat label="Jobs scored" value={result.total_jobs_scored ?? 0} />
        <Stat
          label="Rejected candidates"
          value={result.total_candidates_rejected ?? 0}
        />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        {sourceResults.map((item) => (
          <div
            key={item.source}
            className={[
              "rounded border p-3 text-sm",
              sourceTone(item.status).panelClass,
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="font-medium text-[#171923]">
                {sourceLabel(item.source)}
              </div>
              <span className={`rounded px-2 py-1 text-xs ${sourceTone(item.status).badgeClass}`}>
                {item.status ?? "unknown"}
              </span>
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[#475467]">
              <Metric label="Created" value={item.jobs_created ?? 0} />
              <Metric label="Existing" value={item.jobs_existing ?? 0} />
              <Metric label="Updated" value={item.jobs_updated ?? 0} />
              <Metric label="Scored" value={item.jobs_scored ?? 0} />
              <Metric
                label="Rejected"
                value={item.candidates_rejected ?? 0}
              />
              <Metric label="Records" value={item.provider_records_seen ?? 0} />
            </dl>
            {item.error || item.reason ? (
              <p className="mt-2 text-xs text-[#667085]">
                {item.error ?? item.reason}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <>
      <dt className="text-[#667085]">{label}</dt>
      <dd className="font-medium text-[#344054]">{value}</dd>
    </>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className="h-48 animate-pulse rounded-md border border-[#d9dee8] bg-white"
        />
      ))}
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
      <h2 className="text-sm font-semibold text-[#991b1b]">
        Recommendations could not load
      </h2>
      <p className="mt-1 text-sm text-[#7f1d1d]">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
      >
        Retry
      </button>
    </div>
  );
}

function EmptyState({
  includeRemoteUnknown,
  includeUnsuitable,
  onFindNewRemoteJobs,
  onIncludeRemoteUnknown,
  onShowStretch,
}: {
  includeRemoteUnknown: boolean;
  includeUnsuitable: boolean;
  onFindNewRemoteJobs: () => void;
  onIncludeRemoteUnknown: () => void;
  onShowStretch: () => void;
}) {
  return (
    <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8">
      <h2 className="text-center text-base font-semibold text-[#171923]">
        No strong remote matches found yet.
      </h2>
      <div className="mx-auto mt-4 grid max-w-3xl gap-3 text-sm text-[#475467] sm:grid-cols-2">
        <button
          type="button"
          onClick={onFindNewRemoteJobs}
          className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-left hover:bg-[#f8fafc]"
        >
          Run remote discovery
        </button>
        <button
          type="button"
          onClick={onIncludeRemoteUnknown}
          disabled={includeRemoteUnknown}
          className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-left hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Include remote-unknown jobs
        </button>
        <button
          type="button"
          onClick={onShowStretch}
          className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-left hover:bg-[#f8fafc]"
        >
          Check stretch opportunities
        </button>
        <div className="rounded border border-[#edf0f5] bg-[#f8fafc] px-3 py-2">
          Run discovery later because sources update over time
        </div>
      </div>
      {includeUnsuitable ? (
        <p className="mt-4 text-center text-xs text-[#667085]">
          Debug mode is enabled, but no unsuitable jobs matched the current filters.
        </p>
      ) : null}
    </div>
  );
}

function discoverySummaryMessage(result: RemoteJobDiscoveryOrchestratorResult) {
  if (result.status === "partial") {
    return "Some sources failed, but successful sources were still processed.";
  }
  if (result.status === "skipped") {
    return "Discovery was skipped because sources are on cooldown or disabled.";
  }
  if (result.status === "failed") {
    return "Remote discovery failed safely. Recommendations were left unchanged.";
  }
  return "Remote discovery completed and recommendations were refreshed.";
}

function discoveryTone(status?: string) {
  if (status === "failed") {
    return {
      textClass: "text-[#991b1b]",
      badgeClass: "bg-[#fee2e2] text-[#991b1b]",
    };
  }
  if (status === "partial" || status === "skipped") {
    return {
      textClass: "text-[#92400e]",
      badgeClass: "bg-[#fef3c7] text-[#92400e]",
    };
  }
  return {
    textClass: "text-[#166534]",
    badgeClass: "bg-[#dcfce7] text-[#166534]",
  };
}

function sourceTone(status?: string) {
  if (status === "failed") {
    return {
      panelClass: "border-[#fecaca] bg-[#fff7f7]",
      badgeClass: "bg-[#fee2e2] text-[#991b1b]",
    };
  }
  if (status === "skipped" || status === "disabled") {
    return {
      panelClass: "border-[#fde68a] bg-[#fffbeb]",
      badgeClass: "bg-[#fef3c7] text-[#92400e]",
    };
  }
  return {
    panelClass: "border-[#bbf7d0] bg-[#f0fdf4]",
    badgeClass: "bg-[#dcfce7] text-[#166534]",
  };
}

function sourceLabel(source: RemoteDiscoverySourceResult["source"]) {
  return (
    {
      himalayas: "Himalayas",
      we_work_remotely: "We Work Remotely",
      remotive: "Remotive",
    }[source] ?? source
  );
}

function summarize(
  jobs: Array<{
    match_tier: string;
    is_stale?: boolean;
  }>,
) {
  return jobs.reduce(
    (acc, job) => {
      if (job.match_tier === "best_match") {
        acc.best += 1;
      }
      if (job.match_tier === "worth_checking") {
        acc.worthChecking += 1;
      }
      if (job.is_stale) {
        acc.stale += 1;
      }
      return acc;
    },
    { best: 0, worthChecking: 0, stale: 0 },
  );
}
