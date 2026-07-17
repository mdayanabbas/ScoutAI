"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ApplicationPipelineAnalytics } from "@/components/applications/ApplicationPipelineAnalytics";
import { PageHeader } from "@/components/layout/PageHeader";
import { decisionStatusLabel } from "@/components/recommendations/RecommendedJobCard";
import {
  formatMatchTier,
  formatRemoteEligibility,
  labelize,
  normalizeExternalUrl,
  sourceAttribution,
} from "@/components/recommendations/recommendation-format";
import { useJobDecisions, useJobDecisionStatusCounts } from "@/hooks/use-job-decisions";
import { buildApplicationPipelineAnalytics } from "@/lib/application-pipeline-analytics";
import { archiveJobDecision, updateJobDecision } from "@/lib/job-decisions-api";
import type {
  JobDecisionListItem,
  JobDecisionPriority,
  JobDecisionStatus,
} from "@/types/job-decision";

const activeColumns: Array<{ status: JobDecisionStatus; label: string }> = [
  { status: "saved", label: "Saved" },
  { status: "interested", label: "Interested" },
  { status: "needs_custom_resume", label: "Needs Resume" },
  { status: "needs_cold_dm", label: "Needs Cold DM" },
  { status: "applied", label: "Applied" },
  { status: "interviewing", label: "Interviewing" },
  { status: "rejected", label: "Rejected" },
  { status: "offer", label: "Offer" },
];

const archivedStatuses = new Set(["archived", "skipped", "not_interested", "dismissed"]);
const allStatusOptions: JobDecisionStatus[] = [
  "saved",
  "interested",
  "needs_custom_resume",
  "needs_cold_dm",
  "applied",
  "interviewing",
  "rejected",
  "offer",
  "skipped",
  "not_interested",
];
const priorityRank: Record<string, number> = { urgent: 4, high: 3, medium: 2, low: 1 };
const nextStatus: Partial<Record<JobDecisionStatus, JobDecisionStatus>> = {
  saved: "interested",
  interested: "needs_custom_resume",
  needs_custom_resume: "applied",
  needs_cold_dm: "applied",
  applied: "interviewing",
  interviewing: "offer",
};
const previousStatus: Partial<Record<JobDecisionStatus, JobDecisionStatus>> = {
  interested: "saved",
  needs_custom_resume: "interested",
  needs_cold_dm: "interested",
  applied: "needs_custom_resume",
  interviewing: "applied",
  rejected: "interviewing",
  offer: "interviewing",
};

export default function ApplicationPipelinePage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [remoteFilter, setRemoteFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [resumeNeededOnly, setResumeNeededOnly] = useState(false);
  const [appliedOnly, setAppliedOnly] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(true);
  const [analyticsMode, setAnalyticsMode] = useState<"all" | "filtered">("all");
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const decisionsQuery = useJobDecisions({ limit: 100, include_archived: true });
  const countsQuery = useJobDecisionStatusCounts();
  const decisions = decisionsQuery.data?.items ?? [];

  const filterOptions = useMemo(() => buildFilterOptions(decisions), [decisions]);
  const visibleDecisions = useMemo(
    () =>
      sortDecisions(
        decisions.filter((decision) =>
          passesFilters(decision, {
            search,
            statusFilter,
            priorityFilter,
            tierFilter,
            remoteFilter,
            sourceFilter,
            resumeNeededOnly,
            appliedOnly,
            showArchived,
          }),
        ),
      ),
    [
      decisions,
      search,
      statusFilter,
      priorityFilter,
      tierFilter,
      remoteFilter,
      sourceFilter,
      resumeNeededOnly,
      appliedOnly,
      showArchived,
    ],
  );
  const grouped = useMemo(() => groupByStatus(visibleDecisions), [visibleDecisions]);
  const allAnalytics = useMemo(() => buildApplicationPipelineAnalytics(decisions), [decisions]);
  const filteredAnalytics = useMemo(
    () => buildApplicationPipelineAnalytics(visibleDecisions),
    [visibleDecisions],
  );
  const analytics = analyticsMode === "filtered" ? filteredAnalytics : allAnalytics;

  async function changeStatus(decision: JobDecisionListItem, decision_status: JobDecisionStatus) {
    setPendingId(decision.id);
    setActionError(null);
    try {
      await updateJobDecision(decision.id, {
        decision_status,
        notes: decision.notes ?? null,
        priority: decision.priority ?? "medium",
        next_action: decision.next_action ?? null,
        fit_summary: decision.fit_summary ?? null,
        concerns: decision.concerns ?? null,
      });
      await decisionsQuery.refetch();
      await countsQuery.refetch();
    } catch {
      setActionError("Could not update job status.");
    } finally {
      setPendingId(null);
    }
  }

  async function archiveDecision(decision: JobDecisionListItem) {
    setPendingId(decision.id);
    setActionError(null);
    try {
      await archiveJobDecision(decision.id);
      await decisionsQuery.refetch();
      await countsQuery.refetch();
    } catch {
      setActionError("Could not update job status.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Application Pipeline"
        description="Move tracked jobs through saved, resume prep, applied, interview and offer stages."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link
              href="#pipeline-analytics"
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Pipeline Analytics
            </Link>
            <Link
              href="/jobs/tracked"
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Tracked Jobs
            </Link>
            <Link
              href="/recommendations"
              className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
            >
              Recommended Jobs
            </Link>
          </div>
        }
      />

      <AnalyticsControls
        show={showAnalytics}
        mode={analyticsMode}
        onShowChange={setShowAnalytics}
        onModeChange={setAnalyticsMode}
      />

      {decisionsQuery.error ? (
        <div className="mb-5 rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          Analytics unavailable.
        </div>
      ) : showAnalytics ? (
        <ApplicationPipelineAnalytics
          analytics={analytics}
          label={
            analyticsMode === "filtered"
              ? "Based on the current filtered board view."
              : "Based on loaded tracked jobs."
          }
        />
      ) : null}

      <PipelineFilters
        search={search}
        statusFilter={statusFilter}
        priorityFilter={priorityFilter}
        tierFilter={tierFilter}
        remoteFilter={remoteFilter}
        sourceFilter={sourceFilter}
        resumeNeededOnly={resumeNeededOnly}
        appliedOnly={appliedOnly}
        showArchived={showArchived}
        options={filterOptions}
        onSearchChange={setSearch}
        onStatusChange={setStatusFilter}
        onPriorityChange={setPriorityFilter}
        onTierChange={setTierFilter}
        onRemoteChange={setRemoteFilter}
        onSourceChange={setSourceFilter}
        onResumeNeededChange={setResumeNeededOnly}
        onAppliedOnlyChange={setAppliedOnly}
        onShowArchivedChange={setShowArchived}
      />

      {actionError ? (
        <div className="mb-4 rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          {actionError}
        </div>
      ) : null}

      {decisionsQuery.isLoading ? <LoadingState /> : null}

      {decisionsQuery.error ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">
            Could not load application pipeline.
          </h2>
          <button
            type="button"
            onClick={() => decisionsQuery.refetch()}
            className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {!decisionsQuery.isLoading && !decisionsQuery.error && decisions.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
          <h2 className="text-base font-semibold text-[#171923]">No tracked jobs yet.</h2>
          <Link href="/recommendations" className="mt-3 inline-block rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white">
            Go to Recommended Jobs
          </Link>
        </div>
      ) : null}

      {!decisionsQuery.error && decisions.length > 0 ? (
        <>
          <section className="overflow-x-auto pb-3">
            <div className="grid min-w-[1540px] grid-cols-8 gap-3">
              {activeColumns.map((column) => (
                <PipelineColumn
                  key={column.status}
                  title={column.label}
                  decisions={grouped[column.status] ?? []}
                  pendingId={pendingId}
                  onChangeStatus={changeStatus}
                  onArchive={archiveDecision}
                />
              ))}
            </div>
          </section>

          {showArchived ? (
            <section className="mt-5">
              <h2 className="mb-3 text-base font-semibold text-[#171923]">
                Archived / skipped / not interested ({grouped.archived_like?.length ?? 0})
              </h2>
              {(grouped.archived_like ?? []).length > 0 ? (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {(grouped.archived_like ?? []).map((decision) => (
                    <PipelineJobCard
                      key={decision.id}
                      decision={decision}
                      pending={pendingId === decision.id}
                      onChangeStatus={changeStatus}
                      onArchive={archiveDecision}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-4 text-sm text-[#667085]">
                  No jobs here.
                </div>
              )}
            </section>
          ) : null}
        </>
      ) : null}
    </>
  );
}

function AnalyticsControls({
  show,
  mode,
  onShowChange,
  onModeChange,
}: {
  show: boolean;
  mode: "all" | "filtered";
  onShowChange: (value: boolean) => void;
  onModeChange: (value: "all" | "filtered") => void;
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 rounded-md border border-[#d9dee8] bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
      <button
        type="button"
        onClick={() => onShowChange(!show)}
        className="w-fit rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
      >
        {show ? "Hide Analytics" : "Show Analytics"}
      </button>
      <div className="flex w-fit rounded border border-[#c8ced8] bg-[#f8fafc] p-1">
        {(["all", "filtered"] as const).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onModeChange(item)}
            className={[
              "rounded px-3 py-1.5 text-sm font-medium",
              mode === item ? "bg-white text-[#171923] shadow-sm" : "text-[#667085]",
            ].join(" ")}
          >
            {item === "all" ? "All Tracked" : "Current Filter"}
          </button>
        ))}
      </div>
    </div>
  );
}

function PipelineFilters({
  search,
  statusFilter,
  priorityFilter,
  tierFilter,
  remoteFilter,
  sourceFilter,
  resumeNeededOnly,
  appliedOnly,
  showArchived,
  options,
  onSearchChange,
  onStatusChange,
  onPriorityChange,
  onTierChange,
  onRemoteChange,
  onSourceChange,
  onResumeNeededChange,
  onAppliedOnlyChange,
  onShowArchivedChange,
}: {
  search: string;
  statusFilter: string;
  priorityFilter: string;
  tierFilter: string;
  remoteFilter: string;
  sourceFilter: string;
  resumeNeededOnly: boolean;
  appliedOnly: boolean;
  showArchived: boolean;
  options: ReturnType<typeof buildFilterOptions>;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onPriorityChange: (value: string) => void;
  onTierChange: (value: string) => void;
  onRemoteChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onResumeNeededChange: (value: boolean) => void;
  onAppliedOnlyChange: (value: boolean) => void;
  onShowArchivedChange: (value: boolean) => void;
}) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <label className="xl:col-span-2">
          <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">
            Search
          </span>
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Title or company"
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm"
          />
        </label>
        <Select label="Status" value={statusFilter} options={allStatusOptions} onChange={onStatusChange} />
        <Select label="Priority" value={priorityFilter} options={options.priorities} onChange={onPriorityChange} />
        <Select label="Match Tier" value={tierFilter} options={options.tiers} onChange={onTierChange} />
        <Select label="Remote" value={remoteFilter} options={options.remote} onChange={onRemoteChange} />
        <Select label="Source" value={sourceFilter} options={options.sources} onChange={onSourceChange} />
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-[#344054]">
        <Checkbox label="Resume needed only" checked={resumeNeededOnly} onChange={onResumeNeededChange} />
        <Checkbox label="Applied only" checked={appliedOnly} onChange={onAppliedOnlyChange} />
        <Checkbox label="Show archived / skipped / not interested" checked={showArchived} onChange={onShowArchivedChange} />
      </div>
    </section>
  );
}

function PipelineColumn({
  title,
  decisions,
  pendingId,
  onChangeStatus,
  onArchive,
}: {
  title: string;
  decisions: JobDecisionListItem[];
  pendingId: string | null;
  onChangeStatus: (decision: JobDecisionListItem, status: JobDecisionStatus) => void;
  onArchive: (decision: JobDecisionListItem) => void;
}) {
  return (
    <div className="rounded-md border border-[#d9dee8] bg-[#f8fafc]">
      <div className="sticky top-0 z-10 rounded-t-md border-b border-[#d9dee8] bg-[#f8fafc] px-3 py-3">
        <h2 className="text-sm font-semibold text-[#171923]">
          {title} ({decisions.length})
        </h2>
      </div>
      <div className="space-y-3 p-3">
        {decisions.length > 0 ? (
          decisions.map((decision) => (
            <PipelineJobCard
              key={decision.id}
              decision={decision}
              pending={pendingId === decision.id}
              onChangeStatus={onChangeStatus}
              onArchive={onArchive}
            />
          ))
        ) : (
          <div className="rounded border border-dashed border-[#c8ced8] bg-white p-4 text-sm text-[#667085]">
            No jobs here.
          </div>
        )}
      </div>
    </div>
  );
}

function PipelineJobCard({
  decision,
  pending,
  onChangeStatus,
  onArchive,
}: {
  decision: JobDecisionListItem;
  pending: boolean;
  onChangeStatus: (decision: JobDecisionListItem, status: JobDecisionStatus) => void;
  onArchive: (decision: JobDecisionListItem) => void;
}) {
  const status = statusOf(decision);
  const applyUrl = normalizeExternalUrl(decision.apply_url) ?? normalizeExternalUrl(decision.job_url);
  const source = sourceAttribution(decision.job_url);
  const previous = previousStatus[status];
  const next = nextStatus[status];
  const isApplied = status === "applied" || Boolean(decision.applied_at);
  const needsResume = status === "needs_custom_resume";
  const highPriority = decision.priority === "high" || decision.priority === "urgent";

  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-3 shadow-sm">
      <div className="flex flex-wrap gap-1">
        <Badge>{decisionStatusLabel(status)}</Badge>
        {decision.priority ? <Badge>{labelize(decision.priority)}</Badge> : null}
        {needsResume ? <Badge>Needs Resume</Badge> : null}
        {isApplied ? <Badge>Applied</Badge> : null}
        {highPriority ? <Badge>High Priority</Badge> : null}
      </div>
      <h3 className="mt-3 text-sm font-semibold leading-5 text-[#171923]">
        {decision.title ?? decision.job_title ?? "Tracked job"}
      </h3>
      <p className="mt-1 text-sm text-[#667085]">{decision.company_name ?? "Unknown company"}</p>
      <dl className="mt-3 grid gap-2 text-xs text-[#475467]">
        <Fact label="Match" value={decision.match_tier ? formatMatchTier(decision.match_tier) : "Not scored"} />
        <Fact label="Score" value={decision.total_score == null ? "Not scored" : String(Math.round(decision.total_score))} />
        <Fact label="Remote" value={formatRemoteEligibility(decision.remote_eligibility)} />
        <Fact label="Source" value={source.label.replace("Source: ", "")} />
        {decision.applied_at ? <Fact label="Applied" value={formatDate(decision.applied_at)} /> : null}
      </dl>

      {decision.next_action ? (
        <p className="mt-3 rounded border border-[#edf0f5] bg-[#fcfcfd] px-2 py-1.5 text-xs text-[#344054]">
          <span className="font-medium">Next:</span> {decision.next_action}
        </p>
      ) : null}
      {decision.fit_summary ? (
        <p className="mt-2 line-clamp-3 text-xs leading-5 text-[#475467]">{decision.fit_summary}</p>
      ) : null}
      {decision.notes ? (
        <p className="mt-2 line-clamp-3 text-xs leading-5 text-[#667085]">
          <span className="font-medium">Notes:</span> {decision.notes}
        </p>
      ) : null}

      <div className="mt-3 grid gap-2">
        <Link
          href={`/jobs/${decision.job_id}/workspace`}
          className="rounded border border-[#c8ced8] bg-white px-2 py-1.5 text-center text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          Open Workspace
        </Link>
        {applyUrl ? (
          <a
            href={applyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded bg-[#172033] px-2 py-1.5 text-center text-xs font-medium text-white hover:bg-[#0f1728]"
          >
            View Job / Apply
          </a>
        ) : null}
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            disabled={pending || !previous}
            onClick={() => previous && onChangeStatus(decision, previous)}
            className="rounded border border-[#c8ced8] px-2 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={pending || !next}
            onClick={() => next && onChangeStatus(decision, next)}
            className="rounded border border-[#c8ced8] px-2 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
          </button>
        </div>
        <select
          value={status}
          disabled={pending}
          onChange={(event) => onChangeStatus(decision, event.target.value)}
          className="rounded border border-[#c8ced8] px-2 py-1.5 text-xs"
        >
          {allStatusOptions.map((item) => (
            <option key={item} value={item}>
              {decisionStatusLabel(item)}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={pending}
          onClick={() => onArchive(decision)}
          className="rounded border border-[#fecaca] px-2 py-1.5 text-xs font-medium text-[#991b1b] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Archive
        </button>
      </div>
    </article>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option in statusLabelMap ? statusLabelMap[option] : labelize(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-[#c8ced8]"
      />
      {label}
    </label>
  );
}

function Badge({ children }: { children: string }) {
  return (
    <span className="rounded-full border border-[#d9dee8] bg-[#f8fafc] px-2 py-0.5 text-xs font-medium text-[#475467]">
      {children}
    </span>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-[#667085]">{label}</dt>
      <dd className="text-right font-medium text-[#344054]">{value}</dd>
    </div>
  );
}

function LoadingState() {
  return (
    <section className="overflow-x-auto pb-3">
      <div className="grid min-w-[1540px] grid-cols-8 gap-3">
        {activeColumns.map((column) => (
          <div key={column.status} className="h-96 animate-pulse rounded-md border border-[#d9dee8] bg-white" />
        ))}
      </div>
    </section>
  );
}

const statusLabelMap: Record<string, string> = Object.fromEntries(
  allStatusOptions.map((status) => [status, decisionStatusLabel(status)]),
);

function passesFilters(
  decision: JobDecisionListItem,
  filters: {
    search: string;
    statusFilter: string;
    priorityFilter: string;
    tierFilter: string;
    remoteFilter: string;
    sourceFilter: string;
    resumeNeededOnly: boolean;
    appliedOnly: boolean;
    showArchived: boolean;
  },
) {
  const status = statusOf(decision);
  const archivedLike = archivedStatuses.has(status);
  if (!filters.showArchived && archivedLike) {
    return false;
  }
  if (filters.statusFilter && status !== filters.statusFilter) {
    return false;
  }
  if (filters.priorityFilter && decision.priority !== filters.priorityFilter) {
    return false;
  }
  if (filters.tierFilter && decision.match_tier !== filters.tierFilter) {
    return false;
  }
  if (filters.remoteFilter && decision.remote_eligibility !== filters.remoteFilter) {
    return false;
  }
  if (filters.sourceFilter && sourceAttribution(decision.job_url).label !== filters.sourceFilter) {
    return false;
  }
  if (filters.resumeNeededOnly && status !== "needs_custom_resume") {
    return false;
  }
  if (filters.appliedOnly && status !== "applied") {
    return false;
  }
  const query = filters.search.trim().toLowerCase();
  if (query) {
    const haystack = `${decision.title ?? ""} ${decision.job_title ?? ""} ${decision.company_name ?? ""}`.toLowerCase();
    if (!haystack.includes(query)) {
      return false;
    }
  }
  return true;
}

function groupByStatus(decisions: JobDecisionListItem[]) {
  return decisions.reduce<Record<string, JobDecisionListItem[]>>((acc, decision) => {
    const status = statusOf(decision);
    const key = archivedStatuses.has(status) ? "archived_like" : status;
    acc[key] = [...(acc[key] ?? []), decision];
    return acc;
  }, {});
}

function sortDecisions(decisions: JobDecisionListItem[]) {
  return [...decisions].sort((a, b) => {
    const priorityDelta = priorityValue(b.priority) - priorityValue(a.priority);
    if (priorityDelta) return priorityDelta;
    const scoreDelta = (b.total_score ?? -1) - (a.total_score ?? -1);
    if (scoreDelta) return scoreDelta;
    return dateValue(b.updated_at ?? b.created_at) - dateValue(a.updated_at ?? a.created_at);
  });
}

function priorityValue(priority?: JobDecisionPriority | null) {
  return priorityRank[priority ?? "medium"] ?? 2;
}

function dateValue(value?: string | null) {
  return value ? new Date(value).getTime() || 0 : 0;
}

function statusOf(decision: JobDecisionListItem): JobDecisionStatus {
  return decision.decision_status ?? decision.status ?? "saved";
}

function buildFilterOptions(decisions: JobDecisionListItem[]) {
  return {
    priorities: unique(decisions.map((decision) => decision.priority).filter(Boolean)),
    tiers: unique(decisions.map((decision) => decision.match_tier).filter(Boolean)),
    remote: unique(decisions.map((decision) => decision.remote_eligibility).filter(Boolean)),
    sources: unique(decisions.map((decision) => sourceAttribution(decision.job_url).label).filter(Boolean)),
  };
}

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}
