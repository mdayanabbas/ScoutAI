"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingState } from "@/components/ui/AppState";
import { applicationFollowUpStorage } from "@/lib/application-follow-ups";
import { APP_ROUTES } from "@/lib/app-routes";
import { getSavedColdDmDrafts } from "@/lib/cold-dm-draft";
import { fetchCompanyWatchlist, fetchCompanyWatchlistStats } from "@/lib/company-watchlist-api";
import { dailyOperatingLoopStorage } from "@/lib/daily-operating-loop";
import { fetchDiscoveryRuns } from "@/lib/discovery-api";
import {
  buildJobSearchAnalyticsMarkdown,
  buildJobSearchAnalyticsModel,
  timeRangeLabel,
  type ConversionMetric,
  type FunnelStage,
  type JobSearchAnalyticsModel,
  type JobSearchAnalyticsTimeRange,
  type OutreachTypeRow,
  type WeeklyTrendBucket,
} from "@/lib/job-search-analytics";
import { getJobDecisionStatusCounts, listJobDecisions } from "@/lib/job-decisions-api";
import { fetchRecommendedJobMatches } from "@/lib/job-matches-api";
import { getResumeFitCache } from "@/lib/resume-aware-review-ranking";
import { fetchActiveResume } from "@/lib/resumes-api";
import type { SourceQualityAdvisorItem } from "@/lib/source-quality-advisor";

const timeRanges: Array<{ value: JobSearchAnalyticsTimeRange; label: string }> = [
  { value: "all", label: "All time" },
  { value: "last_7", label: "Last 7 days" },
  { value: "last_30", label: "Last 30 days" },
  { value: "this_week", label: "This week" },
  { value: "this_month", label: "This month" },
];

export default function JobSearchAnalyticsPage() {
  const [timeRange, setTimeRange] = useState<JobSearchAnalyticsTimeRange>("all");
  const [message, setMessage] = useState<string | null>(null);
  const decisionsQuery = useQuery({ queryKey: ["job-search-analytics", "decisions"], queryFn: () => listJobDecisions({ limit: 200, include_archived: true }), retry: 1 });
  const countsQuery = useQuery({ queryKey: ["job-search-analytics", "decision-counts"], queryFn: getJobDecisionStatusCounts, retry: 1 });
  const recommendedQuery = useQuery({ queryKey: ["job-search-analytics", "recommended"], queryFn: () => fetchRecommendedJobMatches({ order_by: "recommended", limit: 100 }), retry: 1 });
  const discoveryRunsQuery = useQuery({ queryKey: ["job-search-analytics", "discovery-runs"], queryFn: () => fetchDiscoveryRuns({ limit: 100 }), retry: 1 });
  const watchlistQuery = useQuery({ queryKey: ["job-search-analytics", "watchlist"], queryFn: () => fetchCompanyWatchlist({ limit: 100 }), retry: 1 });
  const watchlistStatsQuery = useQuery({ queryKey: ["job-search-analytics", "watchlist-stats"], queryFn: fetchCompanyWatchlistStats, retry: 1 });
  const activeResumeQuery = useQuery({ queryKey: ["job-search-analytics", "active-resume"], queryFn: fetchActiveResume, retry: 1 });

  const localFollowUps = useMemo(() => applicationFollowUpStorage.getFollowUps(), []);
  const coldDmDrafts = useMemo(() => getSavedColdDmDrafts(), []);
  const dailyLoops = useMemo(() => dailyOperatingLoopStorage.getAllLoops(), []);
  const resumeFitItems = useMemo(() => getResumeFitCache(), []);

  const model = useMemo(
    () =>
      buildJobSearchAnalyticsModel({
        decisions: decisionsQuery.data?.items ?? [],
        decisionStatusCounts: countsQuery.data ?? null,
        recommendedJobs: recommendedQuery.data?.items ?? [],
        discoveryRuns: discoveryRunsQuery.data?.items ?? [],
        watchlistItems: watchlistQuery.data?.items ?? [],
        watchlistStats: watchlistStatsQuery.data ?? null,
        followUps: localFollowUps,
        coldDmDrafts,
        dailyLoops,
        resumeFitItems,
        activeResume: activeResumeQuery.data ?? null,
        timeRange,
      }),
    [
      activeResumeQuery.data,
      coldDmDrafts,
      countsQuery.data,
      dailyLoops,
      decisionsQuery.data?.items,
      discoveryRunsQuery.data?.items,
      localFollowUps,
      recommendedQuery.data?.items,
      resumeFitItems,
      timeRange,
      watchlistQuery.data?.items,
      watchlistStatsQuery.data,
    ],
  );

  const queryWarnings = [
    decisionsQuery.error ? "Job decisions unavailable." : null,
    countsQuery.error ? "Decision status counts unavailable." : null,
    recommendedQuery.error ? "Recommended jobs unavailable." : null,
    discoveryRunsQuery.error ? "Discovery runs unavailable." : null,
    watchlistQuery.error ? "Company watchlist unavailable." : null,
    activeResumeQuery.error ? "Active resume unavailable." : null,
  ].filter(Boolean) as string[];
  const loadingSections =
    decisionsQuery.isLoading ||
    recommendedQuery.isLoading ||
    discoveryRunsQuery.isLoading ||
    watchlistQuery.isLoading ||
    activeResumeQuery.isLoading;

  const noData =
    model.summary.totalJobsTracked === 0 &&
    model.summary.discoveryRuns === 0 &&
    model.summary.coldDmDrafted === 0 &&
    model.outreach.manuallySent === 0 &&
    model.followUps.sent === 0;

  async function copySummary() {
    setMessage(null);
    try {
      await navigator.clipboard.writeText(buildJobSearchAnalyticsMarkdown(model, timeRange));
      setMessage("Copied analytics summary.");
    } catch {
      setMessage("Could not copy analytics summary.");
    }
  }

  function downloadMarkdown() {
    setMessage(null);
    try {
      const blob = new Blob([buildJobSearchAnalyticsMarkdown(model, timeRange)], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `scoutai-job-search-analytics-${timeRange}.md`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setMessage("Downloaded analytics report.");
    } catch {
      setMessage("Could not download analytics report.");
    }
  }

  return (
    <>
      <PageHeader
        title="Job Search Analytics"
        description="Track your job-search funnel, outreach activity, source quality, and weekly progress."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={APP_ROUTES.commandCenter} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Command Center</Link>
            <Link href={APP_ROUTES.pipeline} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Pipeline</Link>
            <Link href={APP_ROUTES.discovery} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Discovery Control</Link>
            <Link href={APP_ROUTES.followUps} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Follow-ups</Link>
          </div>
        }
      />

      {message ? <Notice>{message}</Notice> : null}
      {loadingSections ? <div className="mb-4"><LoadingState message="Loading job-search analytics..." /></div> : null}
      {queryWarnings.length ? <Notice tone="warning">{`Partial analytics: ${queryWarnings.join(" ")}`}</Notice> : null}
      {model.warnings.map((warning) => <Notice key={warning} tone="warning">{warning}</Notice>)}

      <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {timeRanges.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setTimeRange(item.value)}
                className={`rounded px-3 py-2 text-sm font-medium ${timeRange === item.value ? "bg-[#172033] text-white" : "border border-[#c8ced8] text-[#344054] hover:bg-[#f8fafc]"}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={copySummary} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Copy Analytics Summary</button>
            <button type="button" onClick={downloadMarkdown} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Download Markdown Report</button>
          </div>
        </div>
      </section>

      {noData ? (
        <section className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
          <h2 className="text-base font-semibold text-[#171923]">No job-search analytics yet.</h2>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-[#667085]">Run Daily Scout and start reviewing jobs to generate metrics.</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <Link href={APP_ROUTES.discovery} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white">Open Discovery Control Center</Link>
            <Link href={APP_ROUTES.commandCenter} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054]">Open Command Center</Link>
          </div>
        </section>
      ) : (
        <>
          <OverviewSection model={model} />
          <FunnelSection model={model} />
          <OutreachSection model={model} />
          <SourcePerformanceSection model={model} />
          <WeeklyTrendsSection buckets={model.weeklyTrends} />
          <BottlenecksSection model={model} />
          <NextActionsSection model={model} />
        </>
      )}
    </>
  );
}

function OverviewSection({ model }: { model: JobSearchAnalyticsModel }) {
  return (
    <section className="mb-5">
      <SectionTitle title="Overview" subtitle={`Showing ${timeRangeLabel(model.timeRange).toLowerCase()} metrics.`} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
        {model.summary.metrics.map((item) => (
          <Metric key={item.id} label={item.label} value={item.value} estimated={item.estimated} tone={item.id === "overdue_followups" && item.value > 0 ? "danger" : "default"} />
        ))}
      </div>
    </section>
  );
}

function FunnelSection({ model }: { model: JobSearchAnalyticsModel }) {
  return (
    <section className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
      <div className="rounded-md border border-[#d9dee8] bg-white p-5">
        <SectionTitle title="Funnel" subtitle="Horizontal bars show each stage as a share of the recommended or reviewed base." compact />
        <div className="space-y-3">
          {model.funnel.map((stage) => <FunnelRow key={stage.id} stage={stage} />)}
        </div>
      </div>
      <div className="rounded-md border border-[#d9dee8] bg-white p-5">
        <SectionTitle title="Conversion Rates" subtitle="Zero denominators show as not enough data." compact />
        <div className="space-y-3">
          {model.conversions.map((item) => <ConversionRow key={item.id} item={item} />)}
        </div>
      </div>
    </section>
  );
}

function OutreachSection({ model }: { model: JobSearchAnalyticsModel }) {
  return (
    <section className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="rounded-md border border-[#d9dee8] bg-white p-5">
        <SectionTitle title="Outreach" subtitle="Cold DM drafts and manually tracked follow-ups from local workflow data." compact />
        {model.outreach.draftsCreated + model.outreach.draftsCopied + model.outreach.manuallySent === 0 ? (
          <Empty text="No outreach tracked yet. Draft or track cold DMs from the Application Action Center." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
                <tr>
                  <th className="py-2 pr-4 font-semibold">Type</th>
                  <th className="py-2 pr-4 font-semibold">Drafted</th>
                  <th className="py-2 pr-4 font-semibold">Copied</th>
                  <th className="py-2 pr-4 font-semibold">Sent</th>
                  <th className="py-2 pr-4 font-semibold">Follow-up Sent</th>
                  <th className="py-2 pr-4 font-semibold">Responded</th>
                  <th className="py-2 pr-4 font-semibold">No Response</th>
                  <th className="py-2 pr-4 font-semibold">Closed</th>
                </tr>
              </thead>
              <tbody>
                {model.outreach.byType.filter(hasOutreach).map((row) => <OutreachRow key={row.type} row={row} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="rounded-md border border-[#d9dee8] bg-white p-5">
        <SectionTitle title="Follow-up Risk" subtitle={model.followUps.riskLabel} compact />
        <div className="grid gap-3">
          <Metric label="Due Today" value={model.followUps.dueToday} />
          <Metric label="Overdue" value={model.followUps.overdue} tone={model.followUps.overdue ? "danger" : "default"} />
          <Metric label="Upcoming" value={model.followUps.upcoming} />
          <Metric label="Responded" value={model.followUps.responded} />
          <Metric label="No Response" value={model.followUps.noResponse} />
          <Metric label="Closed" value={model.followUps.closed} />
        </div>
      </div>
    </section>
  );
}

function SourcePerformanceSection({ model }: { model: JobSearchAnalyticsModel }) {
  const ranking = model.sourceAnalytics.ranking;
  const cards = [
    { label: "Best by jobs scored", source: ranking.bestByJobsScored, detail: (item: SourceQualityAdvisorItem) => `${item.totalJobsScored} scored jobs` },
    { label: "Best by quality", source: ranking.bestByQuality, detail: (item: SourceQualityAdvisorItem) => `${item.qualityScore}/100 quality` },
    { label: "Noisiest source", source: ranking.noisiest, detail: (item: SourceQualityAdvisorItem) => `${item.noiseScore ?? "n/a"}/100 noise` },
    { label: "Most failure-prone", source: ranking.mostFailureProne, detail: (item: SourceQualityAdvisorItem) => `${item.failedRuns} failed runs` },
    { label: "Slowest source", source: ranking.slowest, detail: (item: SourceQualityAdvisorItem) => formatDuration(item.averageDurationMs) },
  ];
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionTitle title="Source Performance" subtitle="Discovery source quality from recent run history. Missing fields are treated as unknown, not zero signal." compact />
      {!model.sourceAnalytics.sources.some((item) => item.totalRuns > 0) ? <Empty text="No discovery runs found yet." /> : null}
      <div className="mb-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {cards.map((card) => (
          <div key={card.label} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
            <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{card.label}</p>
            {card.source ? (
              <>
                <p className="mt-1 text-base font-semibold text-[#171923]">{card.source.displayName}</p>
                <p className="mt-1 text-sm text-[#667085]">{card.detail(card.source)}</p>
              </>
            ) : <p className="mt-2 text-sm text-[#667085]">Not enough data</p>}
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
            <tr>
              <th className="py-2 pr-4 font-semibold">Source</th>
              <th className="py-2 pr-4 font-semibold">Runs</th>
              <th className="py-2 pr-4 font-semibold">Success</th>
              <th className="py-2 pr-4 font-semibold">Partial</th>
              <th className="py-2 pr-4 font-semibold">Failed</th>
              <th className="py-2 pr-4 font-semibold">Created</th>
              <th className="py-2 pr-4 font-semibold">Existing</th>
              <th className="py-2 pr-4 font-semibold">Enriched</th>
              <th className="py-2 pr-4 font-semibold">Scored</th>
              <th className="py-2 pr-4 font-semibold">Quality</th>
              <th className="py-2 pr-4 font-semibold">Noise</th>
              <th className="py-2 pr-4 font-semibold">Cadence</th>
            </tr>
          </thead>
          <tbody>
            {model.sourceAnalytics.sources.map((source) => (
              <tr key={source.source} className="border-b border-[#f2f4f7] last:border-0">
                <td className="py-2 pr-4 font-medium text-[#171923]">{source.displayName}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.totalRuns}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.successfulRuns}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.partialRuns}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.failedRuns}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.totalJobsCreated}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.totalJobsExisting}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.totalJobsEnriched}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.totalJobsScored}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.qualityScore}/100</td>
                <td className="py-2 pr-4 text-[#475467]">{source.noiseScore ?? "n/a"}</td>
                <td className="py-2 pr-4 text-[#475467]">{source.suggestedCadence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function WeeklyTrendsSection({ buckets }: { buckets: WeeklyTrendBucket[] }) {
  const max = Math.max(1, ...buckets.map((item) => item.decisionsCreated + item.jobsApplied + item.coldDmDrafted + item.discoveryRuns));
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionTitle title="Weekly Trends" subtitle="Weekly activity buckets from decisions, outreach, discovery runs, and completed daily loops." compact />
      {!buckets.length ? <Empty text="No dated activity found for weekly trends yet." /> : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
              <tr>
                <th className="py-2 pr-4 font-semibold">Week</th>
                <th className="py-2 pr-4 font-semibold">Activity</th>
                <th className="py-2 pr-4 font-semibold">Created</th>
                <th className="py-2 pr-4 font-semibold">Saved</th>
                <th className="py-2 pr-4 font-semibold">Applied</th>
                <th className="py-2 pr-4 font-semibold">DMs Drafted</th>
                <th className="py-2 pr-4 font-semibold">DMs Sent</th>
                <th className="py-2 pr-4 font-semibold">Follow-ups Sent</th>
                <th className="py-2 pr-4 font-semibold">Discovery Runs</th>
                <th className="py-2 pr-4 font-semibold">Loops Done</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map((bucket) => <WeeklyRow key={bucket.week} bucket={bucket} max={max} />)}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function BottlenecksSection({ model }: { model: JobSearchAnalyticsModel }) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionTitle title="Bottlenecks" subtitle="Deterministic checks for where the job search is getting stuck." compact />
      {!model.bottlenecks.length ? <Empty text="No major bottlenecks detected right now." /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {model.bottlenecks.map((item) => (
            <article key={item.id} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
              <Badge tone={item.severity === "high" ? "danger" : item.severity === "medium" ? "warning" : "default"}>{labelize(item.severity)}</Badge>
              <h3 className="mt-3 text-base font-semibold text-[#171923]">{item.title}</h3>
              <p className="mt-1 text-sm text-[#667085]">{item.reason}</p>
              <p className="mt-2 text-sm text-[#344054]">{item.suggestedAction}</p>
              <Link href={item.href} className="mt-3 inline-block text-sm font-medium text-[#175cd3]">Open</Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function NextActionsSection({ model }: { model: JobSearchAnalyticsModel }) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionTitle title="Next Actions" subtitle="Concrete actions derived from the current analytics view." compact />
      {!model.nextActions.length ? <Empty text="No urgent next actions right now." /> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {model.nextActions.map((item) => (
            <article key={item.id} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
              <Badge tone={item.priority === "high" ? "danger" : item.priority === "medium" ? "warning" : "default"}>{labelize(item.priority)}</Badge>
              <h3 className="mt-3 text-base font-semibold text-[#171923]">{item.label}</h3>
              <p className="mt-1 text-sm text-[#667085]">{item.reason}</p>
              <Link href={item.href} className="mt-3 inline-block rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open</Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function FunnelRow({ stage }: { stage: FunnelStage }) {
  return (
    <div>
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="font-medium text-[#344054]">{stage.label}</span>
        <span className="text-[#667085]">{stage.count} · {stage.previousRateLabel} from previous · {stage.baseRateLabel} base</span>
      </div>
      <div className="h-2 rounded bg-[#eef2f6]">
        <div className="h-2 rounded bg-[#172033]" style={{ width: `${stage.basePercent}%` }} />
      </div>
    </div>
  );
}

function ConversionRow({ item }: { item: ConversionMetric }) {
  const width = item.value === null ? 0 : Math.max(4, Math.min(100, item.value));
  return (
    <div>
      <div className="mb-1 flex justify-between gap-3 text-sm">
        <span className="text-[#344054]">{item.label}</span>
        <span className="font-medium text-[#171923]">{item.labelValue}</span>
      </div>
      <div className="h-2 rounded bg-[#eef2f6]">
        <div className="h-2 rounded bg-[#16a34a]" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function OutreachRow({ row }: { row: OutreachTypeRow }) {
  return (
    <tr className="border-b border-[#f2f4f7] last:border-0">
      <td className="py-2 pr-4 font-medium text-[#171923]">{labelize(row.type)}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.drafted}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.copied}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.sentManually}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.followUpSent}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.responded}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.noResponse}</td>
      <td className="py-2 pr-4 text-[#475467]">{row.closed}</td>
    </tr>
  );
}

function WeeklyRow({ bucket, max }: { bucket: WeeklyTrendBucket; max: number }) {
  const total = bucket.decisionsCreated + bucket.jobsApplied + bucket.coldDmDrafted + bucket.discoveryRuns;
  return (
    <tr className="border-b border-[#f2f4f7] last:border-0">
      <td className="py-2 pr-4 font-medium text-[#171923]">{bucket.week}</td>
      <td className="py-2 pr-4">
        <div className="h-2 min-w-28 rounded bg-[#eef2f6]">
          <div className="h-2 rounded bg-[#175cd3]" style={{ width: `${Math.round((total / max) * 100)}%` }} />
        </div>
      </td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.decisionsCreated}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.jobsSaved}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.jobsApplied}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.coldDmDrafted}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.dmsSentManually}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.followUpsSent}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.discoveryRuns}</td>
      <td className="py-2 pr-4 text-[#475467]">{bucket.dailyLoopsCompleted}</td>
    </tr>
  );
}

function SectionTitle({ title, subtitle, compact = false }: { title: string; subtitle?: string; compact?: boolean }) {
  return (
    <div className={compact ? "mb-4" : "mb-3"}>
      <h2 className="text-lg font-semibold text-[#171923]">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-[#667085]">{subtitle}</p> : null}
    </div>
  );
}

function Metric({ label, value, estimated, tone = "default" }: { label: string; value: number; estimated?: boolean; tone?: "default" | "danger" }) {
  return (
    <div className={`rounded border p-3 ${tone === "danger" ? "border-[#fecaca] bg-[#fff7f7]" : "border-[#e4e7ec] bg-white"}`}>
      <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[#171923]">{value}</p>
      {estimated ? <p className="mt-1 text-xs text-[#667085]">Estimated</p> : null}
    </div>
  );
}

function Badge({ children, tone = "default" }: { children: string; tone?: "default" | "warning" | "danger" }) {
  const style = tone === "danger" ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]" : tone === "warning" ? "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]" : "border-[#e4e7ec] bg-white text-[#475467]";
  return <span className={`rounded border px-2 py-1 text-xs font-medium ${style}`}>{children}</span>;
}

function Empty({ text }: { text: string }) {
  return <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4 text-sm text-[#667085]">{text}</div>;
}

function Notice({ children, tone = "default" }: { children: string; tone?: "default" | "warning" }) {
  const style = tone === "warning" ? "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]" : "border-[#d9dee8] bg-white text-[#344054]";
  return <div className={`mb-4 rounded-md border px-4 py-3 text-sm ${style}`}>{children}</div>;
}

function hasOutreach(row: OutreachTypeRow) {
  return row.drafted + row.copied + row.sentManually + row.followUpSent + row.responded + row.noResponse + row.closed > 0;
}

function labelize(value?: string | null) {
  return (value ?? "unknown").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDuration(value?: number | null) {
  if (value == null) return "Not enough data";
  if (value < 1000) return `${value}ms`;
  const seconds = Math.round(value / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
