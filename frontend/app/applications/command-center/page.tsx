"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { applicationFollowUpStorage } from "@/lib/application-follow-ups";
import {
  buildApplicationCommandCenterModel,
  type ApplicationCommandCenterModel,
  type CommandCenterAction,
  type CommandCenterTask,
} from "@/lib/application-command-center";
import { getSavedColdDmDrafts } from "@/lib/cold-dm-draft";
import { fetchCompanyWatchlist, fetchCompanyWatchlistStats } from "@/lib/company-watchlist-api";
import { fetchDiscoveryRuns } from "@/lib/discovery-api";
import { listJobDecisions, getJobDecisionStatusCounts, saveJobDecision, updateJobDecision } from "@/lib/job-decisions-api";
import { fetchRecommendedJobMatches } from "@/lib/job-matches-api";
import { getResumeFitCache } from "@/lib/resume-aware-review-ranking";
import { fetchActiveResume } from "@/lib/resumes-api";
import type { JobDecisionListItem, JobDecisionStatus } from "@/types/job-decision";
import type { RecommendedJobMatch } from "@/types/job-match";

type Filter = "today" | "needs_action" | "resume" | "cold_dm" | "follow_up" | "applications" | "watchlist" | "discovery";

const filters: Array<{ value: Filter; label: string }> = [
  { value: "today", label: "Today" },
  { value: "needs_action", label: "Needs action" },
  { value: "resume", label: "Resume" },
  { value: "cold_dm", label: "Cold DM" },
  { value: "follow_up", label: "Follow-up" },
  { value: "applications", label: "Applications" },
  { value: "watchlist", label: "Watchlist" },
  { value: "discovery", label: "Discovery" },
];

export default function ApplicationCommandCenterPage() {
  const [filter, setFilter] = useState<Filter>("today");
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingJobId, setPendingJobId] = useState<string | null>(null);
  const decisionsQuery = useQuery({ queryKey: ["command-center", "decisions"], queryFn: () => listJobDecisions({ limit: 100, include_archived: true }), retry: 1 });
  const countsQuery = useQuery({ queryKey: ["command-center", "decision-counts"], queryFn: getJobDecisionStatusCounts, retry: 1 });
  const recommendedQuery = useQuery({ queryKey: ["command-center", "recommended"], queryFn: () => fetchRecommendedJobMatches({ order_by: "recommended", limit: 50 }), retry: 1 });
  const resumeQuery = useQuery({ queryKey: ["command-center", "active-resume"], queryFn: fetchActiveResume, retry: 1 });
  const watchlistQuery = useQuery({ queryKey: ["command-center", "watchlist"], queryFn: () => fetchCompanyWatchlist({ limit: 100 }), retry: 1 });
  const watchlistStatsQuery = useQuery({ queryKey: ["command-center", "watchlist-stats"], queryFn: fetchCompanyWatchlistStats, retry: 1 });
  const discoveryRunsQuery = useQuery({ queryKey: ["command-center", "discovery-runs"], queryFn: () => fetchDiscoveryRuns({ limit: 20 }), retry: 1 });
  const localFollowUps = useMemo(() => applicationFollowUpStorage.getFollowUps(), []);
  const coldDrafts = useMemo(() => getSavedColdDmDrafts(), []);
  const resumeFitItems = useMemo(() => getResumeFitCache(), []);
  const decisions = decisionsQuery.data?.items ?? [];
  const model = useMemo(
    () =>
      buildApplicationCommandCenterModel({
        decisions,
        decisionStatusCounts: countsQuery.data ?? null,
        recommendedJobs: recommendedQuery.data?.items ?? [],
        activeResume: resumeQuery.data ?? null,
        watchlistItems: watchlistQuery.data?.items ?? [],
        watchlistStats: watchlistStatsQuery.data ?? null,
        discoveryRuns: discoveryRunsQuery.data ?? null,
        followUps: localFollowUps,
        coldDmDrafts: coldDrafts,
        resumeFitItems,
      }),
    [coldDrafts, countsQuery.data, decisions, discoveryRunsQuery.data, localFollowUps, recommendedQuery.data?.items, resumeFitItems, resumeQuery.data, watchlistQuery.data?.items, watchlistStatsQuery.data],
  );
  const queryErrors = [
    decisionsQuery.error ? "Job decisions unavailable." : null,
    recommendedQuery.error ? "Recommended jobs unavailable." : null,
    resumeQuery.error ? "Active resume unavailable." : null,
    watchlistQuery.error ? "Company watchlist unavailable." : null,
    discoveryRunsQuery.error ? "Discovery runs unavailable." : null,
  ].filter(Boolean) as string[];

  async function updateReviewDecision(job: RecommendedJobMatch, status: JobDecisionStatus) {
    setPendingJobId(job.job_id);
    setActionError(null);
    try {
      await saveJobDecision(job.job_id, { decision_status: status, priority: status === "needs_custom_resume" || status === "needs_cold_dm" ? "high" : "medium" });
      await decisionsQuery.refetch();
      await countsQuery.refetch();
      setMessage(`${job.title} marked as ${labelize(status)}.`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not update decision.");
    } finally {
      setPendingJobId(null);
    }
  }

  async function updateDecision(decision: JobDecisionListItem, status: JobDecisionStatus) {
    setPendingJobId(decision.job_id);
    setActionError(null);
    try {
      await updateJobDecision(decision.id, { decision_status: status, priority: decision.priority ?? "medium" });
      await decisionsQuery.refetch();
      await countsQuery.refetch();
      setMessage(`${decision.title ?? decision.job_title ?? "Job"} marked as ${labelize(status)}.`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not update decision.");
    } finally {
      setPendingJobId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Application Command Center"
        description="Your daily job-search control room for reviews, follow-ups, resume tasks, outreach, and applications."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/discovery/control-center" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Discovery Control</Link>
            <Link href="/applications/follow-ups" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Follow-ups</Link>
            <Link href="/jobs/pipeline" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Pipeline</Link>
          </div>
        }
      />

      {message ? <Notice>{message}</Notice> : null}
      {actionError ? <Notice tone="danger">{actionError}</Notice> : null}
      {queryErrors.length ? <Notice tone="warning">{`Partial dashboard: ${queryErrors.join(" ")}`}</Notice> : null}
      {model.warnings.map((warning) => <Notice key={warning} tone="warning">{warning}</Notice>)}

      <SummaryGrid model={model} />
      <FilterTabs active={filter} onChange={setFilter} />

      {(filter === "today" || filter === "needs_action") ? (
        <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
          <SectionHeader title="Today's Priorities" href="/applications/follow-ups" />
          <ActionList actions={model.todayPriorities} />
        </section>
      ) : null}

      {(filter === "today" || filter === "needs_action") ? (
        <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
          <SectionHeader title="Next Best Actions" href="/discovery/control-center" />
          <ActionList actions={model.nextBestActions} />
        </section>
      ) : null}

      {(filter === "today" || filter === "needs_action") ? (
        <JobsToReviewSection
          jobs={recommendedQuery.data?.items ?? []}
          decisions={decisions}
          pendingJobId={pendingJobId}
          onDecision={updateReviewDecision}
        />
      ) : null}

      {(filter === "resume" || filter === "needs_action") ? <TaskSection title="Resume Tasks" tasks={model.resumeTasks} empty="No resume tasks right now." /> : null}
      {(filter === "cold_dm" || filter === "needs_action") ? <ColdDmSection tasks={model.coldDmTasks} /> : null}
      {(filter === "follow_up" || filter === "needs_action") ? <FollowUpSection tasks={model.followUpTasks} /> : null}
      {(filter === "applications" || filter === "today") ? (
        <PipelineSnapshot model={model} decisions={decisions} pendingJobId={pendingJobId} onDecision={updateDecision} />
      ) : null}
      {filter === "watchlist" ? <TaskSection title="Company Watch Snapshot" tasks={model.watchlistTasks} empty="No companies watched yet." actionHref="/companies/watchlist" /> : null}
      {filter === "discovery" ? <DiscoveryHealth model={model} /> : null}
    </>
  );
}

function SummaryGrid({ model }: { model: ApplicationCommandCenterModel }) {
  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Jobs to Review" value={model.summary.jobsToReview} />
      <Metric label="Resume Tasks" value={model.summary.resumeTasks} />
      <Metric label="Cold DM Tasks" value={model.summary.coldDmTasks} />
      <Metric label="Follow-ups Due" value={model.summary.followUpsDue} />
      <Metric label="Overdue Follow-ups" value={model.summary.overdueFollowUps} tone={model.summary.overdueFollowUps ? "danger" : "default"} />
      <Metric label="Applications In Progress" value={model.summary.applicationsInProgress} />
      <Metric label="Companies Watched" value={model.summary.companiesWatched} />
      <div className="rounded border border-[#e4e7ec] bg-white p-3">
        <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">Active Resume</p>
        <p className="mt-1 text-sm font-semibold text-[#171923]">{model.summary.activeResume}</p>
      </div>
    </section>
  );
}

function JobsToReviewSection({
  jobs,
  decisions,
  pendingJobId,
  onDecision,
}: {
  jobs: RecommendedJobMatch[];
  decisions: JobDecisionListItem[];
  pendingJobId: string | null;
  onDecision: (job: RecommendedJobMatch, status: JobDecisionStatus) => void;
}) {
  const decisionIds = new Set(decisions.map((decision) => decision.job_id));
  const unreviewed = jobs.filter((job) => !decisionIds.has(job.job_id)).slice(0, 8);
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionHeader title="Jobs to Review" href="/recommendations" />
      {!unreviewed.length ? <Empty text="No saved-job review tasks. Review recommendations or run Daily Scout." /> : (
        <div className="grid gap-3">
          {unreviewed.map((job) => (
            <article key={job.job_id} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
                    <Badge>{labelize(job.match_tier)}</Badge>
                    <Badge>{labelize(job.eligibility_status)}</Badge>
                    <Badge>{`Score ${Math.round(job.total_score ?? 0)}`}</Badge>
                    <Badge>{labelize(job.remote_eligibility)}</Badge>
                  </div>
                  <h3 className="mt-3 text-base font-semibold text-[#171923]">{job.title}</h3>
                  <p className="mt-1 text-sm text-[#667085]">{job.company_name ?? "Unknown company"}</p>
                  {job.eligibility_reason ? <p className="mt-2 text-sm text-[#475467]">{job.eligibility_reason}</p> : null}
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  <Link href={`/jobs/${job.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Workspace</Link>
                  {(["saved", "skipped", "needs_custom_resume", "needs_cold_dm"] as JobDecisionStatus[]).map((status) => (
                    <button key={status} type="button" disabled={pendingJobId === job.job_id} onClick={() => onDecision(job, status)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:opacity-60">{labelize(status)}</button>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function TaskSection({ title, tasks, empty, actionHref }: { title: string; tasks: CommandCenterTask[]; empty: string; actionHref?: string }) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionHeader title={title} href={actionHref} />
      {!tasks.length ? <Empty text={empty} /> : <div className="grid gap-3">{tasks.map((task) => <TaskCard key={task.id} task={task} />)}</div>}
    </section>
  );
}

function ColdDmSection({ tasks }: { tasks: CommandCenterTask[] }) {
  return (
    <TaskSection title="Cold DM Tasks" tasks={tasks} empty="No cold DM tasks right now." actionHref="/applications/follow-ups" />
  );
}

function FollowUpSection({ tasks }: { tasks: CommandCenterTask[] }) {
  return (
    <TaskSection title="Follow-ups" tasks={tasks} empty="No follow-ups tracked yet." actionHref="/applications/follow-ups" />
  );
}

function PipelineSnapshot({
  model,
  decisions,
  pendingJobId,
  onDecision,
}: {
  model: ApplicationCommandCenterModel;
  decisions: JobDecisionListItem[];
  pendingJobId: string | null;
  onDecision: (decision: JobDecisionListItem, status: JobDecisionStatus) => void;
}) {
  const top = decisions.filter((decision) => ["applied", "interviewing", "needs_custom_resume", "needs_cold_dm"].includes(decision.decision_status ?? decision.status ?? "saved")).slice(0, 8);
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionHeader title="Application Pipeline Snapshot" href="/jobs/pipeline" />
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Object.entries(model.pipelineCounts).map(([status, count]) => <Metric key={status} label={labelize(status)} value={count} />)}
      </div>
      {!top.length ? <Empty text="No applications in progress yet." /> : (
        <div className="grid gap-3">
          {top.map((decision) => (
            <article key={decision.id} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <Badge>{labelize(decision.decision_status ?? decision.status)}</Badge>
                  <h3 className="mt-3 text-base font-semibold text-[#171923]">{decision.title ?? decision.job_title ?? "Tracked job"}</h3>
                  <p className="mt-1 text-sm text-[#667085]">{decision.company_name ?? "Unknown company"}</p>
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  <Link href={`/jobs/${decision.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Workspace</Link>
                  {(["interested", "applied", "interviewing"] as JobDecisionStatus[]).map((status) => (
                    <button key={status} disabled={pendingJobId === decision.job_id} type="button" onClick={() => onDecision(decision, status)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:opacity-60">{labelize(status)}</button>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function DiscoveryHealth({ model }: { model: ApplicationCommandCenterModel }) {
  const run = model.latestDiscoveryRun;
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <SectionHeader title="Discovery Health" href="/discovery/control-center" />
      <div className="grid gap-3 md:grid-cols-3">
        <Fact label="Latest run" value={run ? formatDate(run.finished_at ?? run.started_at) : "No run found"} />
        <Fact label="Latest source" value={String(run?.source ?? "Unknown")} />
        <Fact label="Status" value={String(run?.status ?? "Not run today")} />
        <Fact label="Warnings" value={String(run?.warnings?.length ?? 0)} />
        <Fact label="Jobs scored" value={String(run?.jobs_scored ?? 0)} />
        <Fact label="Jobs enriched" value={String(run?.jobs_enriched ?? 0)} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/discovery/control-center" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Discovery Control Center</Link>
        <Link href="/discovery/control-center#run-presets" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Run Presets</Link>
        <Link href="/discovery/control-center" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Compare Runs</Link>
      </div>
    </section>
  );
}

function ActionList({ actions }: { actions: CommandCenterAction[] }) {
  if (!actions.length) return <Empty text="No urgent actions right now." />;
  return <div className="grid gap-3">{actions.map((action) => <ActionCard key={action.id} action={action} />)}</div>;
}

function ActionCard({ action }: { action: CommandCenterAction }) {
  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Badge>{labelize(action.priority)}</Badge>
          <h3 className="mt-2 text-base font-semibold text-[#171923]">{action.label}</h3>
          <p className="mt-1 text-sm text-[#667085]">{action.reason}</p>
        </div>
        <Link href={action.href} className="shrink-0 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open</Link>
      </div>
    </article>
  );
}

function TaskCard({ task }: { task: CommandCenterTask }) {
  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
            {task.status ? <Badge>{labelize(task.status)}</Badge> : null}
            {task.score != null ? <Badge>{`Score ${Math.round(task.score)}`}</Badge> : null}
          </div>
          <h3 className="mt-3 text-base font-semibold text-[#171923]">{task.title}</h3>
          <p className="mt-1 text-sm text-[#667085]">{task.company ?? "Unknown company"}</p>
          <p className="mt-2 text-sm text-[#475467]">{task.reason}</p>
          {typeof task.metadata?.draft_preview === "string" ? <p className="mt-2 text-sm text-[#344054]">{task.metadata.draft_preview}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link href={task.href} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Workspace</Link>
          {task.secondaryHref ? <Link href={task.secondaryHref} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Board</Link> : null}
        </div>
      </div>
    </article>
  );
}

function FilterTabs({ active, onChange }: { active: Filter; onChange: (value: Filter) => void }) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="flex flex-wrap gap-2">
        {filters.map((item) => (
          <button key={item.value} type="button" onClick={() => onChange(item.value)} className={`rounded px-3 py-2 text-sm font-medium ${active === item.value ? "bg-[#172033] text-white" : "border border-[#c8ced8] text-[#344054] hover:bg-[#f8fafc]"}`}>
            {item.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function SectionHeader({ title, href }: { title: string; href?: string }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="text-base font-semibold text-[#171923]">{title}</h2>
      {href ? <Link href={href} className="text-sm font-medium text-[#175cd3]">Open</Link> : null}
    </div>
  );
}

function Metric({ label, value, tone = "default" }: { label: string; value: number; tone?: "default" | "danger" }) {
  return <div className={`rounded border p-3 ${tone === "danger" ? "border-[#fecaca] bg-[#fff7f7]" : "border-[#e4e7ec] bg-white"}`}><p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p><p className="mt-1 text-xl font-semibold text-[#171923]">{value}</p></div>;
}

function Badge({ children }: { children?: string | null }) {
  return <span className="rounded border border-[#e4e7ec] bg-white px-2 py-1 text-xs text-[#475467]">{children ?? "Unknown"}</span>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3"><p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p><p className="mt-1 text-sm font-medium text-[#344054]">{value}</p></div>;
}

function Empty({ text }: { text: string }) {
  return <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4 text-sm text-[#667085]">{text}</div>;
}

function Notice({ children, tone = "default" }: { children: string; tone?: "default" | "warning" | "danger" }) {
  const style = tone === "danger" ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]" : tone === "warning" ? "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]" : "border-[#d9dee8] bg-white text-[#344054]";
  return <div className={`mb-4 rounded-md border px-4 py-3 text-sm ${style}`}>{children}</div>;
}

function labelize(value?: string | null) {
  return (value ?? "unknown").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Invalid date" : date.toLocaleString();
}
