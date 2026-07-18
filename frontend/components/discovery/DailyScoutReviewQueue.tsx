"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  normalizeExternalUrl,
} from "@/components/recommendations/recommendation-format";
import type { DailyScoutReviewItem, DailyScoutReviewStatus } from "@/lib/daily-scout-review-queue";
import { buildResumeAwareReviewRanking } from "@/lib/resume-aware-review-ranking";
import type { JobDecisionStatus } from "@/types/job-decision";
import type { ResumeResponse } from "@/types/resume";

type QueueFilter =
  | "all"
  | "unreviewed"
  | "saved"
  | "interested"
  | "needs_custom_resume"
  | "needs_cold_dm"
  | "skipped"
  | "eligible"
  | "stretch"
  | "worth_checking"
  | "watched"
  | "has_salary"
  | "remote"
  | "strong_fit"
  | "good_fit"
  | "needs_tailoring_fit"
  | "weak_fit"
  | "unknown_fit"
  | "apply_now"
  | "tailor_resume"
  | "cold_dm_first"
  | "skip_for_now";

type QueueSort = "recommended" | "resume_fit" | "score" | "newest" | "salary" | "source" | "company";

const decisionActions: Array<{ label: string; status: JobDecisionStatus; reviewStatus: DailyScoutReviewStatus }> = [
  { label: "Save", status: "saved", reviewStatus: "saved" },
  { label: "Interested", status: "interested", reviewStatus: "interested" },
  { label: "Apply later", status: "saved", reviewStatus: "saved" },
  { label: "Needs Resume", status: "needs_custom_resume", reviewStatus: "needs_custom_resume" },
  { label: "Needs Cold DM", status: "needs_cold_dm", reviewStatus: "needs_cold_dm" },
  { label: "Skip", status: "skipped", reviewStatus: "skipped" },
];

export function DailyScoutReviewQueue({
  items,
  loading,
  message,
  error,
  includeSkipped,
  onIncludeSkippedChange,
  onDecisionAction,
  onWatchCompany,
  onOpenedWorkspace,
  onCopyJobUrl,
  onBulkDecisionAction,
  onRunDailyScoutAgain,
  onTryRemoteJobsPreset,
  onTryHnPreset,
  activeResume,
  activeResumeLoading,
  resumeRankLoading,
  resumeRankMessage,
  resumeRankError,
  onRankWithResume,
  onAnalyzeNext,
  onAnalyzeAllVisible,
}: {
  items: DailyScoutReviewItem[];
  loading: boolean;
  message: string | null;
  error: string | null;
  includeSkipped: boolean;
  onIncludeSkippedChange: (value: boolean) => void;
  onDecisionAction: (item: DailyScoutReviewItem, status: JobDecisionStatus, reviewStatus: DailyScoutReviewStatus) => void;
  onWatchCompany: (item: DailyScoutReviewItem) => void;
  onOpenedWorkspace: (item: DailyScoutReviewItem) => void;
  onCopyJobUrl: (item: DailyScoutReviewItem) => void;
  onBulkDecisionAction: (items: DailyScoutReviewItem[], status: JobDecisionStatus, reviewStatus: DailyScoutReviewStatus) => void;
  onRunDailyScoutAgain: () => void;
  onTryRemoteJobsPreset: () => void;
  onTryHnPreset: () => void;
  activeResume?: ResumeResponse | null;
  activeResumeLoading: boolean;
  resumeRankLoading: boolean;
  resumeRankMessage: string | null;
  resumeRankError: string | null;
  onRankWithResume: (items: DailyScoutReviewItem[]) => void;
  onAnalyzeNext: (items: DailyScoutReviewItem[]) => void;
  onAnalyzeAllVisible: (items: DailyScoutReviewItem[]) => void;
}) {
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [sort, setSort] = useState<QueueSort>("recommended");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const sources = useMemo(
    () => Array.from(new Set(items.map((item) => item.source_name ?? item.source_platform).filter(Boolean) as string[])).sort(),
    [items],
  );
  const visibleItems = useMemo(
    () => sortItems(items.filter((item) => matchesFilters(item, { filter, sourceFilter, search })), sort),
    [filter, items, search, sort, sourceFilter],
  );
  const selectedItems = visibleItems.filter((item) => selectedIds.includes(item.job_id));

  return (
    <section id="review-queue" className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Daily Scout Review Queue</h2>
          <p className="mt-1 text-sm text-[#667085]">
            Review jobs from this run and decide what to do next.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#344054]">
          <input
            type="checkbox"
            checked={includeSkipped}
            onChange={(event) => onIncludeSkippedChange(event.target.checked)}
            className="h-4 w-4 accent-[#172033]"
          />
          Include skipped
        </label>
      </div>

      <DailyScoutReviewProgress items={items} />
      <ActiveResumeBanner resume={activeResume} loading={activeResumeLoading} />
      <ResumeFitSummary items={items} />
      {message ? <p className="mt-3 text-sm text-[#166534]">{message}</p> : null}
      {error ? <p className="mt-3 text-sm text-[#991b1b]">{error}</p> : null}
      {resumeRankMessage ? <p className="mt-3 text-sm text-[#175cd3]">{resumeRankMessage}</p> : null}
      {resumeRankError ? <p className="mt-3 text-sm text-[#991b1b]">{resumeRankError}</p> : null}

      <div className="mt-5 grid gap-3 lg:grid-cols-4">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search title, company, source"
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]"
        />
        <select value={filter} onChange={(event) => setFilter(event.target.value as QueueFilter)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="all">All</option>
          <option value="unreviewed">Unreviewed</option>
          <option value="saved">Saved</option>
          <option value="interested">Interested</option>
          <option value="needs_custom_resume">Needs Resume</option>
          <option value="needs_cold_dm">Needs Cold DM</option>
          <option value="skipped">Skipped</option>
          <option value="eligible">Eligible only</option>
          <option value="stretch">Stretch</option>
          <option value="worth_checking">Worth checking</option>
          <option value="watched">Company watched</option>
          <option value="has_salary">Has salary</option>
          <option value="remote">Remote/work from anywhere</option>
          <option value="strong_fit">Strong resume fit</option>
          <option value="good_fit">Good fit</option>
          <option value="needs_tailoring_fit">Needs tailoring</option>
          <option value="weak_fit">Weak fit</option>
          <option value="unknown_fit">Unknown fit</option>
          <option value="apply_now">Apply now</option>
          <option value="tailor_resume">Tailor resume</option>
          <option value="cold_dm_first">Cold DM first</option>
          <option value="skip_for_now">Skip for now</option>
        </select>
        <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="all">All sources</option>
          {sources.map((source) => (
            <option key={source} value={source}>{source}</option>
          ))}
        </select>
        <select value={sort} onChange={(event) => setSort(event.target.value as QueueSort)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="recommended">Recommended</option>
          <option value="resume_fit">Resume Fit</option>
          <option value="score">Score high to low</option>
          <option value="newest">Newest first</option>
          <option value="salary">Salary high to low</option>
          <option value="source">Source</option>
          <option value="company">Company</option>
        </select>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={resumeRankLoading || !visibleItems.length}
          onClick={() => onRankWithResume(visibleItems)}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {resumeRankLoading ? "Ranking with resume..." : "Rank with Resume"}
        </button>
        <button
          type="button"
          disabled={resumeRankLoading || !visibleItems.length}
          onClick={() => onAnalyzeNext(visibleItems)}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Analyze next 10
        </button>
        <button
          type="button"
          disabled={resumeRankLoading || !visibleItems.length}
          onClick={() => onAnalyzeAllVisible(visibleItems)}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Analyze all visible
        </button>
        <button
          type="button"
          disabled={!visibleItems.length}
          onClick={() => setSelectedIds(visibleItems.map((item) => item.job_id))}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Select visible
        </button>
        <button
          type="button"
          disabled={!selectedItems.length}
          onClick={() => onBulkDecisionAction(selectedItems, "saved", "saved")}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Mark selected as saved
        </button>
        <button
          type="button"
          disabled={!selectedItems.length}
          onClick={() => {
            if (window.confirm(`Mark ${selectedItems.length} visible jobs as skipped?`)) {
              onBulkDecisionAction(selectedItems, "skipped", "skipped");
            }
          }}
          className="rounded border border-[#fecaca] px-3 py-2 text-sm font-medium text-[#991b1b] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Mark selected as skipped
        </button>
        <button
          type="button"
          disabled={!selectedItems.length}
          onClick={() => selectedItems.forEach(onWatchCompany)}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Watch companies for selected
        </button>
        <button
          type="button"
          disabled={!selectedIds.length}
          onClick={() => setSelectedIds([])}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Clear selected
        </button>
      </div>

      {loading ? <p className="mt-5 text-sm text-[#667085]">Loading review queue context...</p> : null}

      {!items.length && !loading ? (
        <EmptyQueue
          onRunDailyScoutAgain={onRunDailyScoutAgain}
          onTryRemoteJobsPreset={onTryRemoteJobsPreset}
          onTryHnPreset={onTryHnPreset}
        />
      ) : null}

      {items.length > 0 && !visibleItems.length ? (
        <div className="mt-5 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4 text-sm text-[#667085]">
          No jobs match this filter.
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {visibleItems.map((item) => (
          <DailyScoutReviewCard
            key={item.job_id}
            item={item}
            selected={selectedIds.includes(item.job_id)}
            onSelectedChange={(checked) =>
              setSelectedIds((current) =>
                checked
                  ? Array.from(new Set([...current, item.job_id]))
                  : current.filter((id) => id !== item.job_id),
              )
            }
            onDecisionAction={onDecisionAction}
            onWatchCompany={onWatchCompany}
            onOpenedWorkspace={onOpenedWorkspace}
            onCopyJobUrl={onCopyJobUrl}
          />
        ))}
      </div>
    </section>
  );
}

function ActiveResumeBanner({ resume, loading }: { resume?: ResumeResponse | null; loading: boolean }) {
  return (
    <div className="mt-4 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#344054]">Active Resume</h3>
          {loading ? <p className="mt-1 text-sm text-[#667085]">Checking active resume...</p> : null}
          {!loading && resume ? (
            <p className="mt-1 text-sm text-[#475467]">
              {resume.original_filename ?? resume.filename ?? "Active resume"} / {resume.parse_status ?? "unknown"} / uploaded {formatDate(resume.created_at)}
            </p>
          ) : null}
          {!loading && !resume ? (
            <p className="mt-1 text-sm text-[#667085]">
              No active resume found. Upload or activate a resume to rank jobs by resume fit.
            </p>
          ) : null}
        </div>
        {resume?.is_active ? (
          <span className="self-start rounded border border-[#bbf7d0] bg-[#f0fdf4] px-2.5 py-1 text-xs font-semibold text-[#166534]">
            Active
          </span>
        ) : null}
      </div>
      <Link href="/profile/resume" className="mt-3 inline-block rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
        Open Resume page
      </Link>
      {!resume ? <p className="mt-2 text-sm text-[#667085]">You can continue with generic ranking.</p> : null}
    </div>
  );
}

function ResumeFitSummary({ items }: { items: DailyScoutReviewItem[] }) {
  const summary = buildResumeAwareReviewRanking(items).summary;
  const analyzed = summary.analyzed;
  return (
    <div className="mt-4 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <h3 className="text-sm font-semibold text-[#344054]">Resume Fit Summary</h3>
      {!analyzed ? (
        <p className="mt-2 text-sm text-[#667085]">Run resume ranking to prioritize jobs using your active resume.</p>
      ) : null}
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ProgressMetric label="Analyzed jobs" value={summary.analyzed} />
        <ProgressMetric label="Strong fit" value={summary.strong_fit} />
        <ProgressMetric label="Good fit" value={summary.good_fit} />
        <ProgressMetric label="Needs tailoring" value={summary.needs_tailoring} />
        <ProgressMetric label="Weak fit" value={summary.weak_fit} />
        <ProgressMetric label="Unknown" value={summary.unknown} />
        <ProgressMetric label="Apply now" value={summary.apply_now} />
        <ProgressMetric label="Tailor resume" value={summary.tailor_resume} />
        <ProgressMetric label="Cold DM first" value={summary.cold_dm_first} />
      </div>
    </div>
  );
}

export function DailyScoutReviewProgress({ items }: { items: DailyScoutReviewItem[] }) {
  const counts = {
    total: items.length,
    unreviewed: count(items, "unreviewed"),
    saved: count(items, "saved"),
    interested: count(items, "interested"),
    needsResume: count(items, "needs_custom_resume"),
    needsColdDm: count(items, "needs_cold_dm"),
    skipped: count(items, "skipped") + count(items, "not_interested"),
    watched: items.filter((item) => item.company_watch_status || item.review_status === "watched_company").length,
  };
  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ProgressMetric label="Total queue" value={counts.total} />
        <ProgressMetric label="Unreviewed" value={counts.unreviewed} />
        <ProgressMetric label="Saved" value={counts.saved} />
        <ProgressMetric label="Interested" value={counts.interested} />
        <ProgressMetric label="Needs Resume" value={counts.needsResume} />
        <ProgressMetric label="Needs Cold DM" value={counts.needsColdDm} />
        <ProgressMetric label="Skipped" value={counts.skipped} />
        <ProgressMetric label="Companies watched" value={counts.watched} />
      </div>
      {counts.total > 0 && counts.unreviewed === 0 ? (
        <div className="mt-3 rounded border border-[#bbf7d0] bg-[#f0fdf4] px-3 py-2 text-sm font-medium text-[#166534]">
          Review complete
        </div>
      ) : null}
    </div>
  );
}

function DailyScoutReviewCard({
  item,
  selected,
  onSelectedChange,
  onDecisionAction,
  onWatchCompany,
  onOpenedWorkspace,
  onCopyJobUrl,
}: {
  item: DailyScoutReviewItem;
  selected: boolean;
  onSelectedChange: (checked: boolean) => void;
  onDecisionAction: (item: DailyScoutReviewItem, status: JobDecisionStatus, reviewStatus: DailyScoutReviewStatus) => void;
  onWatchCompany: (item: DailyScoutReviewItem) => void;
  onOpenedWorkspace: (item: DailyScoutReviewItem) => void;
  onCopyJobUrl: (item: DailyScoutReviewItem) => void;
}) {
  const external = normalizeExternalUrl(item.apply_url) ?? normalizeExternalUrl(item.job_url);
  const salary = formatSalary({
    salary_min: item.salary_min,
    salary_max: item.salary_max,
    salary_currency: item.salary_currency,
  });

  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={selected}
              onChange={(event) => onSelectedChange(event.target.checked)}
              className="mt-1 h-4 w-4 accent-[#172033]"
              aria-label={`Select ${item.title}`}
            />
            <div>
              <h3 className="text-base font-semibold text-[#171923]">{item.title}</h3>
              <p className="mt-1 text-sm text-[#667085]">{item.company_name ?? "Unknown company"}</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#475467]">
            <Badge>Score {item.total_score ?? 0}</Badge>
            <Badge>{formatMatchTier(item.match_tier ?? "unknown")}</Badge>
            <Badge>{item.eligibility_status ?? "unknown"}</Badge>
            <Badge>{formatRemoteEligibility(item.remote_eligibility ?? "unknown")}</Badge>
            <Badge>{item.source_name ?? item.source_platform ?? item.created_from}</Badge>
            <Badge>Review {statusLabel(item.review_status)}</Badge>
            {item.decision_status ? <Badge>Decision {statusLabel(item.decision_status)}</Badge> : null}
            {item.company_watch_status ? <Badge>Company watched</Badge> : null}
            {salary ? <Badge>{salary}</Badge> : null}
          </div>
          {item.eligibility_reason ? (
            <p className="mt-3 text-sm leading-6 text-[#344054]">{item.eligibility_reason}</p>
          ) : null}
        </div>
          <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
          {item.resume_action ? <ResumePrimaryAction item={item} onDecisionAction={onDecisionAction} /> : null}
          {decisionActions.map((action) => (
            <button
              key={action.status}
              type="button"
              onClick={() => onDecisionAction(item, action.status, action.reviewStatus)}
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              {action.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onDecisionAction(item, "not_interested", "not_interested")}
            className="rounded border border-[#fecaca] bg-white px-3 py-2 text-sm font-medium text-[#991b1b] hover:bg-[#fff7f7]"
          >
            Not interested
          </button>
          <button type="button" onClick={() => onWatchCompany(item)} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Watch Company
          </button>
          {item.job_id ? (
            <Link href={`/jobs/${item.job_id}/workspace`} onClick={() => onOpenedWorkspace(item)} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
              Open workspace
            </Link>
          ) : null}
          {external ? (
            <a href={external} target="_blank" rel="noopener noreferrer" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Open job URL
            </a>
          ) : null}
          <button type="button" onClick={() => onCopyJobUrl(item)} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Copy Job URL
          </button>
        </div>
      </div>
      <ResumeFitDetails item={item} />
    </article>
  );
}

function ResumePrimaryAction({
  item,
  onDecisionAction,
}: {
  item: DailyScoutReviewItem;
  onDecisionAction: (item: DailyScoutReviewItem, status: JobDecisionStatus, reviewStatus: DailyScoutReviewStatus) => void;
}) {
  if (item.resume_action === "apply_now") {
    return (
      <Link href={`/jobs/${item.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
        Open Workspace
      </Link>
    );
  }
  if (item.resume_action === "tailor_resume") {
    return (
      <Link href={`/jobs/${item.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
        Improve Resume
      </Link>
    );
  }
  if (item.resume_action === "cold_dm_first") {
    return <button type="button" onClick={() => onDecisionAction(item, "needs_cold_dm", "needs_cold_dm")} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Needs Cold DM</button>;
  }
  if (item.resume_action === "create_project_angle") {
    return <button type="button" onClick={() => onDecisionAction(item, "needs_custom_resume", "needs_custom_resume")} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Needs Resume</button>;
  }
  if (item.resume_action === "skip_for_now") {
    return <button type="button" onClick={() => onDecisionAction(item, "skipped", "skipped")} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Skip</button>;
  }
  return null;
}

function ResumeFitDetails({ item }: { item: DailyScoutReviewItem }) {
  if (!item.resume_analysis_status || item.resume_analysis_status === "not_started") return null;
  if (item.resume_analysis_status === "loading") {
    return <div className="mt-4 rounded border border-[#bfdbfe] bg-[#eff6ff] p-3 text-sm text-[#1d4ed8]">Resume analysis loading...</div>;
  }
  if (item.resume_analysis_status === "failed") {
    return <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">{item.resume_analysis_error ?? "Resume analysis failed."}</div>;
  }
  if (item.resume_analysis_status === "unavailable") {
    return <div className="mt-4 rounded border border-[#e4e7ec] bg-white p-3 text-sm text-[#667085]">Unknown resume fit. Not enough resume/job evidence.</div>;
  }
  return (
    <div className="mt-4 rounded border border-[#dbeafe] bg-[#eff6ff] p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-[#1d4ed8]">
        <Badge>Resume Fit {item.resume_fit_score ?? "unknown"}</Badge>
        <Badge>{resumeTierLabel(item.resume_fit_tier)}</Badge>
        <Badge>{resumeActionLabel(item.resume_action)}</Badge>
      </div>
      {item.resume_fit_summary ? <p className="mt-3 text-sm text-[#344054]">{item.resume_fit_summary}</p> : null}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <CompactList title="Strengths" items={item.resume_strengths ?? []} emptyText="No clear strengths." />
        <CompactList title="Gaps" items={item.resume_gaps ?? []} emptyText="No major gaps." />
      </div>
      {((item.resume_strengths?.length ?? 0) > 2 || (item.resume_gaps?.length ?? 0) > 2) ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm font-medium text-[#175cd3]">More resume fit details</summary>
          <div className="mt-2 grid gap-3 md:grid-cols-2">
            <FullList title="All strengths" items={item.resume_strengths ?? []} />
            <FullList title="All gaps" items={item.resume_gaps ?? []} />
          </div>
        </details>
      ) : null}
    </div>
  );
}

function CompactList({ title, items, emptyText }: { title: string; items: string[]; emptyText: string }) {
  const shown = items.slice(0, 2);
  return (
    <div>
      <h4 className="text-sm font-semibold text-[#344054]">{title}</h4>
      {shown.length ? (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-[#475467]">
          {shown.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : <p className="mt-1 text-sm text-[#667085]">{emptyText}</p>}
    </div>
  );
}

function FullList({ title, items }: { title: string; items: string[] }) {
  return <CompactList title={title} items={items} emptyText="None." />;
}

function EmptyQueue({
  onRunDailyScoutAgain,
  onTryRemoteJobsPreset,
  onTryHnPreset,
}: {
  onRunDailyScoutAgain: () => void;
  onTryRemoteJobsPreset: () => void;
  onTryHnPreset: () => void;
}) {
  return (
    <div className="mt-5 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <p className="text-sm font-semibold text-[#344054]">No jobs to review from this run.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={onRunDailyScoutAgain} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Run Daily Scout again
        </button>
        <button type="button" onClick={onTryRemoteJobsPreset} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Try Remote Jobs Only preset
        </button>
        <button type="button" onClick={onTryHnPreset} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Try HN Startup Signals
        </button>
        <Link href="/recommendations" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
          Open Recommended Jobs
        </Link>
      </div>
    </div>
  );
}

function matchesFilters(
  item: DailyScoutReviewItem,
  { filter, sourceFilter, search }: { filter: QueueFilter; sourceFilter: string; search: string },
) {
  if (sourceFilter !== "all" && (item.source_name ?? item.source_platform) !== sourceFilter) return false;
  const term = search.trim().toLowerCase();
  if (term) {
    const haystack = [item.title, item.company_name, item.source_name, item.source_platform].join(" ").toLowerCase();
    if (!haystack.includes(term)) return false;
  }
  if (filter === "all") return true;
  if (filter === "eligible") return item.eligibility_status === "eligible";
  if (filter === "stretch") return item.eligibility_status === "stretch" || item.match_tier === "stretch";
  if (filter === "worth_checking") return item.match_tier === "worth_checking";
  if (filter === "watched") return Boolean(item.company_watch_status || item.review_status === "watched_company");
  if (filter === "has_salary") return item.salary_min !== null && item.salary_min !== undefined;
  if (filter === "remote") return String(item.remote_eligibility ?? "").includes("remote") || item.remote_eligibility === "work_from_anywhere";
  if (filter === "strong_fit") return item.resume_fit_tier === "strong_fit";
  if (filter === "good_fit") return item.resume_fit_tier === "good_fit";
  if (filter === "needs_tailoring_fit") return item.resume_fit_tier === "needs_tailoring";
  if (filter === "weak_fit") return item.resume_fit_tier === "weak_fit";
  if (filter === "unknown_fit") return !item.resume_fit_tier || item.resume_fit_tier === "unknown";
  if (filter === "apply_now") return item.resume_action === "apply_now";
  if (filter === "tailor_resume") return item.resume_action === "tailor_resume";
  if (filter === "cold_dm_first") return item.resume_action === "cold_dm_first";
  if (filter === "skip_for_now") return item.resume_action === "skip_for_now";
  return item.review_status === filter;
}

function sortItems(items: DailyScoutReviewItem[], sort: QueueSort) {
  const cloned = [...items];
  if (sort === "resume_fit") return buildResumeAwareReviewRanking(cloned).rankedItems;
  if (sort === "score") return cloned.sort((a, b) => (b.total_score ?? 0) - (a.total_score ?? 0));
  if (sort === "salary") return cloned.sort((a, b) => salaryValue(b) - salaryValue(a));
  if (sort === "source") return cloned.sort((a, b) => String(a.source_name ?? a.source_platform ?? "").localeCompare(String(b.source_name ?? b.source_platform ?? "")));
  if (sort === "company") return cloned.sort((a, b) => String(a.company_name ?? "").localeCompare(String(b.company_name ?? "")));
  if (sort === "newest") return cloned;
  return cloned;
}

function salaryValue(item: DailyScoutReviewItem) {
  const value = typeof item.salary_max === "number" ? item.salary_max : Number(item.salary_max ?? item.salary_min ?? 0);
  return Number.isFinite(value) ? value : 0;
}

function count(items: DailyScoutReviewItem[], status: DailyScoutReviewStatus) {
  return items.filter((item) => item.review_status === status).length;
}

function ProgressMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
      <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[#171923]">{value}</p>
    </div>
  );
}

function Badge({ children }: { children: ReactNode }) {
  return <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{children}</span>;
}

function statusLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function resumeTierLabel(value?: string) {
  if (!value || value === "unknown") return "Unknown resume fit";
  if (value === "strong_fit") return "Strong resume fit";
  if (value === "good_fit") return "Good fit";
  if (value === "needs_tailoring") return "Needs tailoring";
  return "Weak fit";
}

function resumeActionLabel(value?: string) {
  if (!value) return "Needs review";
  return statusLabel(value);
}

function formatDate(value?: string | null) {
  if (!value) return "unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}
