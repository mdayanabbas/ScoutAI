import { buildFollowUpDashboard, dueDateState, needsAction, type ApplicationFollowUpItem } from "@/lib/application-follow-ups";
import type { ResumeFitCacheEntry } from "@/lib/resume-aware-review-ranking";
import type { SavedColdDmDraft } from "@/lib/cold-dm-draft";
import type { CompanyWatchlistResponse, CompanyWatchlistStatsResponse } from "@/types/company-watchlist";
import type { DiscoveryRunListItem, DiscoveryRunsResponse } from "@/types/discovery";
import type { JobDecisionListItem, JobDecisionStatus, JobDecisionStatusCounts } from "@/types/job-decision";
import type { RecommendedJobMatch } from "@/types/job-match";
import type { ResumeResponse } from "@/types/resume";

export type CommandCenterAction = {
  id: string;
  label: string;
  reason: string;
  priority: "high" | "medium" | "low";
  href: string;
  actionType: string;
};

export type CommandCenterTask = {
  id: string;
  title: string;
  company?: string | null;
  reason: string;
  status?: string | null;
  score?: number | null;
  href: string;
  secondaryHref?: string;
  metadata?: Record<string, unknown>;
};

export type ApplicationCommandCenterModel = {
  summary: {
    jobsToReview: number;
    resumeTasks: number;
    coldDmTasks: number;
    followUpsDue: number;
    overdueFollowUps: number;
    applicationsInProgress: number;
    companiesWatched: number;
    activeResume: string;
  };
  todayPriorities: CommandCenterAction[];
  reviewTasks: CommandCenterTask[];
  resumeTasks: CommandCenterTask[];
  coldDmTasks: CommandCenterTask[];
  followUpTasks: CommandCenterTask[];
  applicationTasks: CommandCenterTask[];
  watchlistTasks: CommandCenterTask[];
  discoveryTasks: CommandCenterTask[];
  nextBestActions: CommandCenterAction[];
  warnings: string[];
  pipelineCounts: Record<string, number>;
  latestDiscoveryRun?: DiscoveryRunListItem | null;
};

export type ApplicationCommandCenterInput = {
  decisions?: JobDecisionListItem[] | null;
  decisionStatusCounts?: JobDecisionStatusCounts | null;
  recommendedJobs?: RecommendedJobMatch[] | null;
  activeResume?: ResumeResponse | null;
  watchlistItems?: CompanyWatchlistResponse[] | null;
  watchlistStats?: CompanyWatchlistStatsResponse | null;
  discoveryRuns?: DiscoveryRunsResponse | DiscoveryRunListItem[] | null;
  followUps?: ApplicationFollowUpItem[] | null;
  coldDmDrafts?: SavedColdDmDraft[] | null;
  resumeFitItems?: ResumeFitCacheEntry[] | null;
};

const inProgressStatuses = new Set(["applied", "interviewing"]);
const terminalFollowUpStatuses = new Set(["follow_up_sent", "responded", "closed"]);

export function buildApplicationCommandCenterModel(
  input: ApplicationCommandCenterInput,
  now = new Date(),
): ApplicationCommandCenterModel {
  const decisions = input.decisions ?? [];
  const decisionByJobId = new Map(decisions.map((decision) => [decision.job_id, decision]));
  const recommended = input.recommendedJobs ?? [];
  const watchlist = input.watchlistItems ?? [];
  const followUps = input.followUps ?? [];
  const coldDrafts = input.coldDmDrafts ?? [];
  const resumeFitItems = input.resumeFitItems ?? [];
  const runs = Array.isArray(input.discoveryRuns) ? input.discoveryRuns : input.discoveryRuns?.items ?? [];
  const latestDiscoveryRun = [...runs].sort((a, b) => dateValue(b.finished_at ?? b.started_at) - dateValue(a.finished_at ?? a.started_at))[0] ?? null;
  const followUpDashboard = buildFollowUpDashboard(followUps, now);
  const reviewJobs = recommended.filter((job) => job.job_id && !decisionByJobId.has(job.job_id)).slice(0, 10);
  const resumeDecisions = decisions.filter((decision) => statusOf(decision) === "needs_custom_resume");
  const resumeFitTasks = resumeFitItems.filter((item) => item.resume_action === "tailor_resume" || item.resume_action === "create_project_angle" || item.resume_fit_tier === "needs_tailoring");
  const coldDmDecisions = decisions.filter((decision) => statusOf(decision) === "needs_cold_dm");
  const unsentDrafts = coldDrafts.filter((draft) => !followUps.some((item) => item.draft_id === draft.id && ["sent_manually", "follow_up_sent", "responded", "closed"].includes(item.outreach_status)));
  const draftedOrCopied = followUps.filter((item) => item.outreach_status === "drafted" || item.outreach_status === "copied");
  const applications = decisions.filter((decision) => inProgressStatuses.has(statusOf(decision)));
  const warnings: string[] = [];

  if (!input.activeResume) warnings.push("No active resume found. Upload or activate a resume to enable resume-aware ranking.");
  if (!latestDiscoveryRun || !isSameLocalDay(latestDiscoveryRun.finished_at ?? latestDiscoveryRun.started_at, now)) {
    warnings.push("No Daily Scout run found for today.");
  }

  const reviewTasks = reviewJobs.map((job) => taskFromRecommended(job, "Review this recommended job before it goes stale."));
  const resumeTasks = [
    ...resumeDecisions.map((decision) => taskFromDecision(decision, "Marked as needing resume tailoring.")),
    ...resumeFitTasks.map((fit) => ({
      id: `resume-fit-${fit.job_id}`,
      title: `Resume fit task for ${fit.job_id}`,
      reason: fit.resume_action === "create_project_angle" ? "Needs a project angle before applying." : "Resume fit suggests tailoring.",
      status: fit.resume_fit_tier,
      score: fit.resume_fit_score,
      href: `/jobs/${fit.job_id}/workspace`,
    })),
  ].slice(0, 12);
  const coldDmTasks = [
    ...coldDmDecisions.map((decision) => taskFromDecision(decision, "Marked as needing cold outreach.")),
    ...draftedOrCopied.map((item) => taskFromFollowUp(item, item.outreach_status === "copied" ? "Draft copied but not marked sent." : "Draft exists but has not been copied or sent.")),
    ...unsentDrafts.map((draft) => ({
      id: `draft-${draft.id}`,
      title: draft.job_title ?? "Saved cold DM draft",
      company: draft.company_name,
      reason: "Saved cold DM draft has not been tracked as sent.",
      status: draft.targetType,
      href: draft.job_id ? `/jobs/${draft.job_id}/workspace` : "/applications/follow-ups",
      secondaryHref: "/applications/follow-ups",
      metadata: { draft_preview: draft.body.slice(0, 160) },
    })),
  ].slice(0, 12);
  const followUpTasks = followUps
    .filter((item) => needsAction(item, now) || ["sent_manually", "responded"].includes(item.outreach_status))
    .sort((a, b) => followUpRank(a, now) - followUpRank(b, now))
    .slice(0, 12)
    .map((item) => taskFromFollowUp(item, dueReason(item, now)));
  const applicationTasks = decisions
    .filter((decision) => ["applied", "interviewing", "needs_custom_resume", "needs_cold_dm"].includes(statusOf(decision)))
    .slice(0, 10)
    .map((decision) => taskFromDecision(decision, "Application is in progress or needs preparation."));
  const watchlistTasks = watchlist.slice(0, 8).map((item) => ({
    id: `watch-${item.id}`,
    title: item.company_name,
    company: item.company_name,
    reason: item.recommended_job_count ? `${item.recommended_job_count} related recommended jobs.` : "Company is on your watchlist.",
    status: item.priority,
    href: "/companies/watchlist",
    metadata: { latest_job_title: item.latest_job_title },
  }));
  const discoveryTasks = latestDiscoveryRun
    ? [{
        id: `discovery-${latestDiscoveryRun.id ?? "latest"}`,
        title: "Latest discovery run",
        reason: `${latestDiscoveryRun.source ?? "Discovery"} ${latestDiscoveryRun.status ?? "completed"}`,
        status: latestDiscoveryRun.status,
        href: "/discovery/control-center",
        metadata: { warnings: latestDiscoveryRun.warnings?.length ?? 0 },
      }]
    : [{
        id: "run-daily-scout",
        title: "Run Daily Scout",
        reason: "No recent discovery run found for today.",
        status: "not_run_today",
        href: "/discovery/control-center",
      }];

  const todayPriorities = buildPriorities({
    followUps,
    decisions,
    reviewTasks,
    resumeTasks,
    coldDmTasks,
    watchlistTasks,
    latestDiscoveryRun,
    now,
  });

  const nextBestActions = todayPriorities.slice(0, 7);
  const pipelineCounts = buildPipelineCounts(decisions, input.decisionStatusCounts);

  return {
    summary: {
      jobsToReview: reviewTasks.length,
      resumeTasks: resumeDecisions.length + resumeFitTasks.length,
      coldDmTasks: coldDmDecisions.length + draftedOrCopied.length + unsentDrafts.length,
      followUpsDue: followUpDashboard.dueToday,
      overdueFollowUps: followUpDashboard.overdue,
      applicationsInProgress: applications.length,
      companiesWatched: Number(input.watchlistStats?.total ?? watchlist.length),
      activeResume: activeResumeLabel(input.activeResume),
    },
    todayPriorities,
    reviewTasks,
    resumeTasks,
    coldDmTasks,
    followUpTasks,
    applicationTasks,
    watchlistTasks,
    discoveryTasks,
    nextBestActions,
    warnings,
    pipelineCounts,
    latestDiscoveryRun,
  };
}

function buildPriorities(input: {
  followUps: ApplicationFollowUpItem[];
  decisions: JobDecisionListItem[];
  reviewTasks: CommandCenterTask[];
  resumeTasks: CommandCenterTask[];
  coldDmTasks: CommandCenterTask[];
  watchlistTasks: CommandCenterTask[];
  latestDiscoveryRun?: DiscoveryRunListItem | null;
  now: Date;
}) {
  const actions: CommandCenterAction[] = [];
  const overdue = input.followUps.filter((item) => dueDateState(item, input.now) === "overdue");
  const dueToday = input.followUps.filter((item) => dueDateState(item, input.now) === "due_today");
  const interviewing = input.decisions.filter((decision) => statusOf(decision) === "interviewing");
  if (overdue.length) actions.push(action("overdue-follow-ups", `Follow up with ${overdue.length} overdue contact${overdue.length === 1 ? "" : "s"}`, "These follow-ups are past their local due date.", "high", "/applications/follow-ups", "follow_up"));
  if (dueToday.length) actions.push(action("due-today", `Handle ${dueToday.length} follow-up${dueToday.length === 1 ? "" : "s"} due today`, "These outreach follow-ups are due today.", "high", "/applications/follow-ups", "follow_up"));
  if (interviewing.length) actions.push(action("interviewing", `Check ${interviewing.length} interviewing application${interviewing.length === 1 ? "" : "s"}`, "Interviewing roles should stay warm.", "high", "/jobs/pipeline", "application"));
  if (input.resumeTasks.length) actions.push(action("resume-tasks", `Tailor resume for ${input.resumeTasks.length} job${input.resumeTasks.length === 1 ? "" : "s"}`, "These roles need resume work before applying.", "medium", "/jobs/pipeline", "resume"));
  if (input.coldDmTasks.length) actions.push(action("cold-dm", `Prepare or send ${input.coldDmTasks.length} cold DM task${input.coldDmTasks.length === 1 ? "" : "s"}`, "Cold outreach tasks are waiting.", "medium", "/applications/follow-ups", "cold_dm"));
  if (input.reviewTasks.length) actions.push(action("review", `Review ${input.reviewTasks.length} recommended job${input.reviewTasks.length === 1 ? "" : "s"}`, "Recommended jobs without a decision need triage.", "medium", "/recommendations", "review"));
  if (input.watchlistTasks.length) actions.push(action("watchlist", `Check ${input.watchlistTasks.length} watched compan${input.watchlistTasks.length === 1 ? "y" : "ies"}`, "Watchlist companies may have related jobs or need review.", "low", "/companies/watchlist", "watchlist"));
  if (!input.latestDiscoveryRun || !isSameLocalDay(input.latestDiscoveryRun.finished_at ?? input.latestDiscoveryRun.started_at, input.now)) {
    actions.push(action("daily-scout", "Run Daily Scout today", "No discovery run is recorded for today.", "medium", "/discovery/control-center", "discovery"));
  }
  return actions.slice(0, 10);
}

function action(id: string, label: string, reason: string, priority: CommandCenterAction["priority"], href: string, actionType: string): CommandCenterAction {
  return { id, label, reason, priority, href, actionType };
}

function taskFromRecommended(job: RecommendedJobMatch, reason: string): CommandCenterTask {
  return {
    id: `review-${job.job_id}`,
    title: job.title,
    company: job.company_name,
    reason,
    status: job.match_tier,
    score: job.total_score,
    href: `/jobs/${job.job_id}/workspace`,
    secondaryHref: "/recommendations",
    metadata: {
      eligibility: job.eligibility_status,
      remote: job.remote_eligibility,
      source: job.job_url,
    },
  };
}

function taskFromDecision(decision: JobDecisionListItem, reason: string): CommandCenterTask {
  return {
    id: `decision-${decision.id}`,
    title: decision.title ?? decision.job_title ?? "Tracked job",
    company: decision.company_name,
    reason,
    status: statusOf(decision),
    score: decision.total_score,
    href: `/jobs/${decision.job_id}/workspace`,
    secondaryHref: "/jobs/pipeline",
  };
}

function taskFromFollowUp(item: ApplicationFollowUpItem, reason: string): CommandCenterTask {
  return {
    id: `follow-${item.id}`,
    title: item.job_title ?? "Outreach follow-up",
    company: item.company_name,
    reason,
    status: item.outreach_status,
    href: item.workspace_url ?? (item.job_id ? `/jobs/${item.job_id}/workspace` : "/applications/follow-ups"),
    secondaryHref: "/applications/follow-ups",
    metadata: {
      outreach_type: item.outreach_type,
      due: item.follow_up_due_at,
      draft_preview: item.draft_preview,
    },
  };
}

function dueReason(item: ApplicationFollowUpItem, now: Date) {
  const state = dueDateState(item, now);
  if (state === "overdue") return "Follow-up is overdue.";
  if (state === "due_today") return "Follow-up is due today.";
  if (state === "upcoming") return "Follow-up is scheduled.";
  if (item.outreach_status === "copied") return "Draft copied but not marked sent.";
  if (item.outreach_status === "drafted") return "Drafted but not copied or sent.";
  return "Outreach is being tracked.";
}

function buildPipelineCounts(decisions: JobDecisionListItem[], counts?: JobDecisionStatusCounts | null) {
  const result: Record<string, number> = {
    saved: Number(counts?.saved ?? 0),
    interested: Number(counts?.interested ?? 0),
    needs_custom_resume: Number(counts?.needs_custom_resume ?? 0),
    needs_cold_dm: Number(counts?.needs_cold_dm ?? 0),
    applied: Number(counts?.applied ?? 0),
    interviewing: Number(counts?.interviewing ?? 0),
    rejected: Number(counts?.rejected ?? 0),
    offer: Number(counts?.offer ?? 0),
  };
  if (!counts) {
    for (const decision of decisions) {
      const status = statusOf(decision);
      result[status] = (result[status] ?? 0) + 1;
    }
  }
  return result;
}

function statusOf(decision: JobDecisionListItem): JobDecisionStatus {
  return decision.decision_status ?? decision.status ?? "saved";
}

function followUpRank(item: ApplicationFollowUpItem, now: Date) {
  const state = dueDateState(item, now);
  if (state === "overdue") return 0;
  if (state === "due_today") return 1;
  if (item.outreach_status === "copied") return 2;
  if (item.outreach_status === "drafted") return 3;
  if (state === "upcoming") return 4;
  return 5;
}

function activeResumeLabel(resume?: ResumeResponse | null) {
  if (!resume) return "No active resume";
  return `${resume.original_filename ?? resume.filename ?? "Active resume"}${resume.parse_status ? ` (${resume.parse_status})` : ""}`;
}

function dateValue(value?: string | null) {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function isSameLocalDay(value: string | null | undefined, now: Date) {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
}
