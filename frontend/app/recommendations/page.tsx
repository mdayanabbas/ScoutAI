"use client";

import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { RecommendedJobCard } from "@/components/recommendations/RecommendedJobCard";
import { RecommendationFilters } from "@/components/recommendations/RecommendationFilters";
import { useRecommendedJobMatches } from "@/hooks/use-job-matches";
import {
  runHimalayasDiscovery,
  runRemotiveDiscovery,
  runWeWorkRemotelyDiscovery,
} from "@/lib/job-matches-api";
import type {
  DiscoverySourceResult,
  RecommendedJobMatchParams,
} from "@/types/job-match";

export default function RecommendationsPage() {
  const [matchTier, setMatchTier] = useState("");
  const [includeRemoteUnknown, setIncludeRemoteUnknown] = useState(false);
  const [includeUnsuitable, setIncludeUnsuitable] = useState(false);
  const [discoveryResults, setDiscoveryResults] = useState<DiscoverySourceResult[]>([]);
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState<string | null>(null);

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
    setDiscoveryMessage("Searching remote sources...");
    setDiscoveryResults([]);

    const nextResults: DiscoverySourceResult[] = [];
    for (const source of discoverySources) {
      try {
        const result = await source.run();
        nextResults.push({ source: source.name, ok: true, result });
      } catch (error) {
        nextResults.push({
          source: source.name,
          ok: false,
          error: error instanceof Error ? error.message : "Discovery failed",
        });
      }
      setDiscoveryResults([...nextResults]);
    }

    await recommendationsQuery.refetch();
    setDiscoveryRunning(false);
    setDiscoveryMessage(null);
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
              {discoveryRunning ? "Searching remote sources..." : "Find new remote jobs"}
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

      {discoveryResults.length > 0 ? (
        <DiscoverySummary results={discoveryResults} />
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
            <RecommendedJobCard key={job.job_id} job={job} />
          ))}
        </section>
      ) : null}
    </>
  );
}

const discoverySources = [
  { name: "Himalayas" as const, run: runHimalayasDiscovery },
  { name: "We Work Remotely" as const, run: runWeWorkRemotelyDiscovery },
  { name: "Remotive" as const, run: runRemotiveDiscovery },
];

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

function DiscoverySummary({ results }: { results: DiscoverySourceResult[] }) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-sm font-semibold text-[#171923]">Discovery summary</h2>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        {results.map((item) => (
          <div
            key={item.source}
            className={[
              "rounded border p-3 text-sm",
              item.ok
                ? "border-[#bbf7d0] bg-[#f0fdf4]"
                : "border-[#fecaca] bg-[#fff7f7]",
            ].join(" ")}
          >
            <div className="font-medium text-[#171923]">{item.source}</div>
            {item.ok && item.result ? (
              <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[#475467]">
                <Metric label="Status" value={item.result.status ?? "unknown"} />
                <Metric label="Created" value={item.result.jobs_created ?? 0} />
                <Metric label="Existing" value={item.result.jobs_existing ?? 0} />
                <Metric label="Updated" value={item.result.jobs_updated ?? 0} />
                <Metric label="Scored" value={item.result.jobs_scored ?? 0} />
                <Metric
                  label="Rejected"
                  value={item.result.candidates_rejected ?? 0}
                />
              </dl>
            ) : (
              <p className="mt-2 text-[#991b1b]">{item.error}</p>
            )}
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
          Try again later because remote boards update over time
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
