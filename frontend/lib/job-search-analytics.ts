import { buildFollowUpDashboard, dueDateState, type ApplicationFollowUpItem } from "@/lib/application-follow-ups";
import type { SavedColdDmDraft } from "@/lib/cold-dm-draft";
import type { DailyOperatingLoopState } from "@/lib/daily-operating-loop";
import { buildSourceQualityAdvisor, type SourceQualityAdvisorItem } from "@/lib/source-quality-advisor";
import type { CompanyWatchlistResponse, CompanyWatchlistStatsResponse } from "@/types/company-watchlist";
import type { DiscoveryRunListItem } from "@/types/discovery";
import type { JobDecisionListItem, JobDecisionStatusCounts } from "@/types/job-decision";
import type { RecommendedJobMatch } from "@/types/job-match";
import type { ResumeResponse } from "@/types/resume";
import type { ResumeFitCacheEntry } from "@/lib/resume-aware-review-ranking";

export type JobSearchAnalyticsTimeRange = "all" | "last_7" | "last_30" | "this_week" | "this_month";

export type JobSearchAnalyticsInput = {
  decisions?: JobDecisionListItem[] | null;
  decisionStatusCounts?: JobDecisionStatusCounts | null;
  recommendedJobs?: RecommendedJobMatch[] | null;
  discoveryRuns?: DiscoveryRunListItem[] | null;
  watchlistItems?: CompanyWatchlistResponse[] | null;
  watchlistStats?: CompanyWatchlistStatsResponse | null;
  followUps?: ApplicationFollowUpItem[] | null;
  coldDmDrafts?: SavedColdDmDraft[] | null;
  dailyLoops?: DailyOperatingLoopState[] | null;
  resumeFitItems?: ResumeFitCacheEntry[] | null;
  activeResume?: ResumeResponse | null;
  timeRange?: JobSearchAnalyticsTimeRange;
};

export type AnalyticsMetric = {
  id: string;
  label: string;
  value: number;
  estimated?: boolean;
};

export type FunnelStage = {
  id: string;
  label: string;
  count: number;
  previousRateLabel: string;
  baseRateLabel: string;
  basePercent: number;
};

export type ConversionMetric = {
  id: string;
  label: string;
  numerator: number;
  denominator: number;
  value: number | null;
  labelValue: string;
};

export type OutreachTypeRow = {
  type: string;
  drafted: number;
  copied: number;
  sentManually: number;
  followUpSent: number;
  responded: number;
  noResponse: number;
  closed: number;
};

export type SourceRanking = {
  bestByJobsScored: SourceQualityAdvisorItem | null;
  bestByQuality: SourceQualityAdvisorItem | null;
  noisiest: SourceQualityAdvisorItem | null;
  mostFailureProne: SourceQualityAdvisorItem | null;
  slowest: SourceQualityAdvisorItem | null;
};

export type WeeklyTrendBucket = {
  week: string;
  decisionsCreated: number;
  decisionsUpdated: number;
  jobsSaved: number;
  jobsApplied: number;
  coldDmDrafted: number;
  dmsSentManually: number;
  followUpsSent: number;
  discoveryRuns: number;
  dailyLoopsCompleted: number;
};

export type JobSearchBottleneck = {
  id: string;
  severity: "low" | "medium" | "high";
  title: string;
  reason: string;
  suggestedAction: string;
  href: string;
};

export type JobSearchNextAction = {
  id: string;
  label: string;
  reason: string;
  href: string;
  priority: "low" | "medium" | "high";
};

export type JobSearchAnalyticsModel = {
  timeRange: JobSearchAnalyticsTimeRange;
  summary: {
    metrics: AnalyticsMetric[];
    totalJobsTracked: number;
    jobsReviewed: number;
    reviewedIsEstimated: boolean;
    saved: number;
    interested: number;
    applied: number;
    interviewing: number;
    rejected: number;
    offers: number;
    coldDmDrafted: number;
    dmsManuallySent: number;
    followUpsDue: number;
    overdueFollowUps: number;
    companiesWatched: number;
    discoveryRuns: number;
  };
  funnel: FunnelStage[];
  conversions: ConversionMetric[];
  outreach: {
    draftsCreated: number;
    draftsCopied: number;
    manuallySent: number;
    followUpsDue: number;
    overdue: number;
    followUpsSent: number;
    responses: number;
    noResponse: number;
    closed: number;
    byType: OutreachTypeRow[];
  };
  followUps: {
    dueToday: number;
    overdue: number;
    upcoming: number;
    responded: number;
    noResponse: number;
    closed: number;
    sent: number;
    riskLevel: "good" | "medium" | "high";
    riskLabel: string;
  };
  sourceAnalytics: {
    sources: SourceQualityAdvisorItem[];
    ranking: SourceRanking;
  };
  weeklyTrends: WeeklyTrendBucket[];
  bottlenecks: JobSearchBottleneck[];
  nextActions: JobSearchNextAction[];
  warnings: string[];
};

const sourceOrder = ["himalayas", "we_work_remotely", "remotive", "hacker_news", "ycombinator", "ashby"];
const outreachTypes = [
  "founder_dm",
  "recruiter_dm",
  "hiring_manager_dm",
  "team_member_dm",
  "twitter_dm",
  "linkedin_note",
  "email_follow_up",
  "application_follow_up",
  "other",
];

export function buildJobSearchAnalyticsModel(
  input: JobSearchAnalyticsInput,
  now = new Date(),
): JobSearchAnalyticsModel {
  const timeRange = input.timeRange ?? "all";
  const warnings: string[] = [];
  const decisions = filterByRange(input.decisions ?? [], timeRange, now, decisionDate, warnings, "Tracked jobs without dates are only included in all-time analytics.");
  const recommended = filterByRange(input.recommendedJobs ?? [], timeRange, now, recommendationDate, warnings, "Recommended jobs without dates are only included in all-time analytics.");
  const runs = filterByRange(input.discoveryRuns ?? [], timeRange, now, runDate, warnings, "Discovery runs without dates are only included in all-time analytics.");
  const watchlist = filterByRange(input.watchlistItems ?? [], timeRange, now, watchlistDate, warnings, "Watched companies without dates are only included in all-time analytics.");
  const followUps = filterByRange(input.followUps ?? [], timeRange, now, followUpDate, warnings, "Follow-ups without dates are only included in all-time analytics.");
  const coldDrafts = filterByRange(input.coldDmDrafts ?? [], timeRange, now, (item) => item.generatedAt, warnings, "Cold DM drafts without dates are only included in all-time analytics.");
  const dailyLoops = filterByRange(input.dailyLoops ?? [], timeRange, now, loopDate, warnings, "Daily loops without dates are only included in all-time analytics.");
  const resumeFitItems = filterByRange(input.resumeFitItems ?? [], timeRange, now, (item) => item.updated_at, warnings, "Resume-fit cache entries without dates are only included in all-time analytics.");
  const statusCounts = buildStatusCounts(decisions, input.decisionStatusCounts, timeRange);
  const followUpDashboard = buildFollowUpDashboard(followUps, now);
  const jobsReviewed = uniqueCount(decisions.map((item) => item.job_id));
  const reviewedIsEstimated = true;
  const coldDmDrafted = coldDrafts.length;
  const copied = followUps.filter((item) => item.outreach_status === "copied").length;
  const manuallySent = followUps.filter((item) => item.outreach_status === "sent_manually").length;
  const followUpsSent = followUps.filter((item) => item.outreach_status === "follow_up_sent").length;
  const companiesWatched = timeRange === "all" ? Number(input.watchlistStats?.total ?? watchlist.length) : watchlist.length;
  const advisorSources = buildSourceQualityAdvisor({
    runs,
    availableSources: sourceOrder,
  });

  const summary = {
    totalJobsTracked: decisions.length,
    jobsReviewed,
    reviewedIsEstimated,
    saved: statusCounts.saved,
    interested: statusCounts.interested,
    applied: statusCounts.applied,
    interviewing: statusCounts.interviewing,
    rejected: statusCounts.rejected,
    offers: statusCounts.offer,
    coldDmDrafted,
    dmsManuallySent: manuallySent,
    followUpsDue: followUpDashboard.dueToday,
    overdueFollowUps: followUpDashboard.overdue,
    companiesWatched,
    discoveryRuns: runs.length,
    metrics: [] as AnalyticsMetric[],
  };
  summary.metrics = [
    metric("total_tracked", "Total Jobs Tracked", summary.totalJobsTracked),
    metric("reviewed", "Jobs Reviewed", summary.jobsReviewed, summary.reviewedIsEstimated),
    metric("saved", "Saved", summary.saved),
    metric("interested", "Interested", summary.interested),
    metric("applied", "Applied", summary.applied),
    metric("interviewing", "Interviewing", summary.interviewing),
    metric("rejected", "Rejected", summary.rejected),
    metric("offers", "Offers", summary.offers),
    metric("cold_dm_drafted", "Cold DMs Drafted", summary.coldDmDrafted),
    metric("sent_manually", "DMs Manually Sent", summary.dmsManuallySent),
    metric("followups_due", "Follow-ups Due", summary.followUpsDue),
    metric("overdue_followups", "Overdue Follow-ups", summary.overdueFollowUps),
    metric("companies_watched", "Companies Watched", summary.companiesWatched),
    metric("discovery_runs", "Discovery Runs", summary.discoveryRuns),
  ];

  const funnel = buildFunnel(statusCounts, recommended.length, jobsReviewed);
  const conversions = [
    conversion("saved_rate", "Saved / reviewed", statusCounts.saved, jobsReviewed),
    conversion("interested_rate", "Interested / reviewed", statusCounts.interested, jobsReviewed),
    conversion("application_rate", "Applied / interested", statusCounts.applied, statusCounts.interested),
    conversion("interview_rate", "Interviewing / applied", statusCounts.interviewing, statusCounts.applied),
    conversion("offer_rate", "Offers / interviewing", statusCounts.offer, statusCounts.interviewing),
    conversion("rejection_rate", "Rejected / applied", statusCounts.rejected, statusCounts.applied),
    conversion("cold_dm_rate", "Sent / drafted or copied", manuallySent, coldDmDrafted + copied),
    conversion("follow_up_completion_rate", "Follow-ups sent / due", followUpsSent, followUpDashboard.dueToday + followUpDashboard.overdue),
  ];
  const outreach = {
    draftsCreated: coldDmDrafted,
    draftsCopied: copied,
    manuallySent,
    followUpsDue: followUpDashboard.dueToday,
    overdue: followUpDashboard.overdue,
    followUpsSent,
    responses: followUpDashboard.responded,
    noResponse: followUpDashboard.noResponse,
    closed: followUpDashboard.closed,
    byType: buildOutreachRows(followUps),
  };
  const followUpRisk = followUpDashboard.overdue > 5 ? "high" : followUpDashboard.overdue > 0 ? "medium" : "good";
  const model: JobSearchAnalyticsModel = {
    timeRange,
    summary,
    funnel,
    conversions,
    outreach,
    followUps: {
      dueToday: followUpDashboard.dueToday,
      overdue: followUpDashboard.overdue,
      upcoming: followUpDashboard.upcoming,
      responded: followUpDashboard.responded,
      noResponse: followUpDashboard.noResponse,
      closed: followUpDashboard.closed,
      sent: followUpsSent + manuallySent,
      riskLevel: followUpRisk,
      riskLabel: followUpRisk === "high" ? "High risk: overdue follow-ups are piling up." : followUpRisk === "medium" ? "Medium risk: at least one follow-up is overdue." : "Good: no overdue follow-ups detected.",
    },
    sourceAnalytics: {
      sources: advisorSources,
      ranking: buildSourceRanking(advisorSources),
    },
    weeklyTrends: buildWeeklyTrends({ decisions, followUps, runs, coldDrafts, dailyLoops }),
    bottlenecks: [],
    nextActions: [],
    warnings: unique(warnings),
  };
  model.bottlenecks = detectJobSearchBottlenecks(model, {
    activeResume: input.activeResume ?? null,
    resumeFitItems,
    latestRunAt: latestDate(runs.map((run) => run.finished_at ?? run.started_at)),
  });
  model.nextActions = buildNextActions(model, recommended.length);
  return model;
}

export function detectJobSearchBottlenecks(
  model: JobSearchAnalyticsModel,
  context: { activeResume?: ResumeResponse | null; resumeFitItems?: ResumeFitCacheEntry[]; latestRunAt?: Date | null } = {},
): JobSearchBottleneck[] {
  const result: JobSearchBottleneck[] = [];
  const savedOrInterested = model.summary.saved + model.summary.interested;
  const resumeTasks = stageCount(model, "needs_custom_resume");
  const coldDmTasks = stageCount(model, "needs_cold_dm");
  const copiedNotSent = model.outreach.draftsCopied;
  if (savedOrInterested >= 5 && model.summary.applied <= Math.max(1, Math.floor(savedOrInterested * 0.2))) {
    result.push(bottleneck("application", "high", "Application bottleneck", `${savedOrInterested} jobs are saved or interesting, but only ${model.summary.applied} are applied.`, "Apply to the top 3 interested jobs or move them out of the active queue.", "/jobs/pipeline"));
  }
  if (resumeTasks > 0) {
    result.push(bottleneck("resume", resumeTasks > 3 ? "high" : "medium", "Resume bottleneck", `${resumeTasks} jobs need custom resume work.`, "Open workspaces and tailor the highest-fit roles first.", "/jobs/pipeline"));
  }
  if (coldDmTasks + copiedNotSent > 0) {
    result.push(bottleneck("outreach", coldDmTasks + copiedNotSent > 4 ? "high" : "medium", "Outreach bottleneck", `${coldDmTasks + copiedNotSent} cold outreach tasks are waiting.`, "Send copied drafts manually or close stale outreach tasks.", "/applications/follow-ups"));
  }
  if (model.followUps.overdue > 0) {
    result.push(bottleneck("followups", model.followUps.overdue > 5 ? "high" : "medium", "Follow-up bottleneck", `${model.followUps.overdue} follow-up${model.followUps.overdue === 1 ? " is" : "s are"} overdue.`, "Clear overdue follow-ups before drafting more outreach.", "/applications/follow-ups"));
  }
  if (model.funnel[0]?.count >= 10 && model.summary.saved + model.summary.interested < 3) {
    result.push(bottleneck("review", "medium", "Review bottleneck", "Recommendations are available, but few have been saved or marked interesting.", "Review 10 recommendations and make fast save/skip decisions.", "/discovery/control-center#review-queue"));
  }
  if (!context.latestRunAt || daysBetween(context.latestRunAt, new Date()) > 7) {
    result.push(bottleneck("discovery-consistency", "medium", "Discovery consistency bottleneck", "Discovery has not been run this week.", "Run Daily Scout to refresh the top of the funnel.", "/discovery/control-center"));
  }
  if (!context.activeResume) {
    result.push(bottleneck("resume-setup", "medium", "Resume setup bottleneck", "No active resume was available for analytics.", "Upload or activate a resume before ranking jobs by fit.", "/profile/resume"));
  }
  if (model.sourceAnalytics.sources.some((item) => item.failedRuns > 0 || item.totalWarnings > 3 || ["needs_debugging", "needs_configuration"].includes(item.recommendation))) {
    result.push(bottleneck("source-quality", "low", "Discovery source bottleneck", "One or more sources have warnings, failures, or configuration gaps.", "Open Discovery Control Center and review noisy source guidance.", "/discovery/control-center"));
  }
  return result.slice(0, 8);
}

export function buildJobSearchAnalyticsMarkdown(model: JobSearchAnalyticsModel, timeRange = model.timeRange) {
  return [
    `# ScoutAI Job Search Analytics - ${timeRangeLabel(timeRange)}`,
    "",
    "## Overview",
    ...model.summary.metrics.map((item) => `- ${item.label}: ${item.value}${item.estimated ? " (estimated)" : ""}`),
    "",
    "## Funnel",
    ...model.funnel.map((stage) => `- ${stage.label}: ${stage.count} (${stage.baseRateLabel} of base)`),
    "",
    "## Conversion Rates",
    ...model.conversions.map((item) => `- ${item.label}: ${item.labelValue}`),
    "",
    "## Outreach",
    `- Drafts created: ${model.outreach.draftsCreated}`,
    `- Drafts copied: ${model.outreach.draftsCopied}`,
    `- Manually sent: ${model.outreach.manuallySent}`,
    `- Follow-ups sent: ${model.outreach.followUpsSent}`,
    "",
    "## Follow-ups",
    `- Due today: ${model.followUps.dueToday}`,
    `- Overdue: ${model.followUps.overdue}`,
    `- Risk: ${model.followUps.riskLabel}`,
    "",
    "## Source Performance",
    ...model.sourceAnalytics.sources.map((source) => `- ${source.displayName}: ${source.totalRuns} runs, ${source.totalJobsScored} jobs scored, quality ${source.qualityScore}/100, noise ${source.noiseScore ?? "n/a"}`),
    "",
    "## Weekly Trends",
    ...model.weeklyTrends.map((week) => `- ${week.week}: ${week.decisionsCreated} decisions, ${week.jobsApplied} applied, ${week.coldDmDrafted} DMs drafted, ${week.discoveryRuns} discovery runs`),
    "",
    "## Bottlenecks",
    ...(model.bottlenecks.length ? model.bottlenecks.map((item) => `- [${item.severity}] ${item.title}: ${item.suggestedAction}`) : ["- None detected"]),
    "",
    "## Next Actions",
    ...(model.nextActions.length ? model.nextActions.map((item) => `- [${item.priority}] ${item.label}: ${item.reason}`) : ["- No urgent next actions"]),
    "",
  ].join("\n");
}

export function timeRangeLabel(value: JobSearchAnalyticsTimeRange | string) {
  return {
    all: "All time",
    last_7: "Last 7 days",
    last_30: "Last 30 days",
    this_week: "This week",
    this_month: "This month",
  }[value] ?? String(value);
}

function buildStatusCounts(decisions: JobDecisionListItem[], counts?: JobDecisionStatusCounts | null, timeRange: JobSearchAnalyticsTimeRange = "all") {
  const result = {
    saved: 0,
    interested: 0,
    needs_custom_resume: 0,
    needs_cold_dm: 0,
    applied: 0,
    interviewing: 0,
    rejected: 0,
    offer: 0,
    archived: 0,
    skipped: 0,
    not_interested: 0,
  };
  if (!decisions.length && counts && timeRange === "all") {
    for (const key of Object.keys(result) as Array<keyof typeof result>) result[key] = Number(counts[key] ?? 0);
    return result;
  }
  for (const decision of decisions) {
    const status = statusOf(decision);
    if (status in result) result[status as keyof typeof result] += 1;
  }
  return result;
}

function buildFunnel(statusCounts: ReturnType<typeof buildStatusCounts>, recommendedCount: number, reviewedCount: number): FunnelStage[] {
  const stages = [
    ["recommended", "Recommended", recommendedCount],
    ["reviewed", "Reviewed", reviewedCount],
    ["saved", "Saved", statusCounts.saved],
    ["interested", "Interested", statusCounts.interested],
    ["needs_custom_resume", "Needs Resume", statusCounts.needs_custom_resume],
    ["needs_cold_dm", "Needs Cold DM", statusCounts.needs_cold_dm],
    ["applied", "Applied", statusCounts.applied],
    ["interviewing", "Interviewing", statusCounts.interviewing],
    ["offer", "Offer", statusCounts.offer],
    ["rejected", "Rejected", statusCounts.rejected],
    ["archived", "Archived", statusCounts.archived + statusCounts.skipped + statusCounts.not_interested],
  ] as const;
  const base = Math.max(recommendedCount, reviewedCount, 1);
  return stages.map(([id, label, count], index) => {
    const previous = index === 0 ? base : stages[index - 1][2];
    return {
      id,
      label,
      count,
      previousRateLabel: labelRate(count, previous),
      baseRateLabel: labelRate(count, base),
      basePercent: previous > 0 ? Math.min(100, Math.round((count / base) * 100)) : 0,
    };
  });
}

function buildOutreachRows(followUps: ApplicationFollowUpItem[]) {
  return outreachTypes.map((type) => {
    const items = followUps.filter((item) => item.outreach_type === type);
    return {
      type,
      drafted: items.filter((item) => item.outreach_status === "drafted").length,
      copied: items.filter((item) => item.outreach_status === "copied").length,
      sentManually: items.filter((item) => item.outreach_status === "sent_manually").length,
      followUpSent: items.filter((item) => item.outreach_status === "follow_up_sent").length,
      responded: items.filter((item) => item.outreach_status === "responded").length,
      noResponse: items.filter((item) => item.outreach_status === "no_response").length,
      closed: items.filter((item) => item.outreach_status === "closed").length,
    };
  });
}

function buildSourceRanking(sources: SourceQualityAdvisorItem[]): SourceRanking {
  return {
    bestByJobsScored: maxBy(sources, (item) => item.totalJobsScored),
    bestByQuality: maxBy(sources, (item) => item.qualityScore),
    noisiest: maxBy(sources, (item) => item.noiseScore ?? 0),
    mostFailureProne: maxBy(sources, (item) => item.failedRuns),
    slowest: maxBy(sources, (item) => item.averageDurationMs ?? 0),
  };
}

function buildWeeklyTrends(input: {
  decisions: JobDecisionListItem[];
  followUps: ApplicationFollowUpItem[];
  runs: DiscoveryRunListItem[];
  coldDrafts: SavedColdDmDraft[];
  dailyLoops: DailyOperatingLoopState[];
}) {
  const buckets = new Map<string, WeeklyTrendBucket>();
  for (const decision of input.decisions) {
    const created = dateFromValue(decision.created_at);
    const updated = dateFromValue(decision.updated_at ?? decision.last_status_changed_at);
    if (created) {
      const bucket = getWeekBucket(buckets, created);
      bucket.decisionsCreated += 1;
      if (statusOf(decision) === "saved") bucket.jobsSaved += 1;
      if (statusOf(decision) === "applied") bucket.jobsApplied += 1;
    }
    if (updated) getWeekBucket(buckets, updated).decisionsUpdated += 1;
  }
  for (const draft of input.coldDrafts) {
    const date = dateFromValue(draft.generatedAt);
    if (date) getWeekBucket(buckets, date).coldDmDrafted += 1;
  }
  for (const item of input.followUps) {
    const sent = dateFromValue(item.sent_at);
    const followUpSent = dateFromValue(item.follow_up_sent_at);
    if (sent && item.outreach_status === "sent_manually") getWeekBucket(buckets, sent).dmsSentManually += 1;
    if (followUpSent || item.outreach_status === "follow_up_sent") {
      const date = followUpSent ?? dateFromValue(item.updated_at);
      if (date) getWeekBucket(buckets, date).followUpsSent += 1;
    }
  }
  for (const run of input.runs) {
    const date = dateFromValue(run.started_at ?? run.finished_at);
    if (date) getWeekBucket(buckets, date).discoveryRuns += 1;
  }
  for (const loop of input.dailyLoops) {
    const date = dateFromValue(loop.completedAt ?? loop.lastUpdatedAt ?? loop.date);
    if (date && loop.status === "completed") getWeekBucket(buckets, date).dailyLoopsCompleted += 1;
  }
  return Array.from(buckets.values()).sort((a, b) => b.week.localeCompare(a.week)).slice(0, 12);
}

function buildNextActions(model: JobSearchAnalyticsModel, recommendedCount: number): JobSearchNextAction[] {
  const actions: JobSearchNextAction[] = [];
  const interested = model.summary.interested + stageCount(model, "needs_custom_resume") + stageCount(model, "needs_cold_dm");
  if (model.followUps.overdue > 0) actions.push(nextAction("followups", `Follow up on ${model.followUps.overdue} overdue message${model.followUps.overdue === 1 ? "" : "s"}`, "Overdue follow-ups are the highest-leverage cleanup.", "/applications/follow-ups", "high"));
  if (interested > model.summary.applied) actions.push(nextAction("apply", `Apply to ${Math.min(3, interested - model.summary.applied)} interested job${interested - model.summary.applied === 1 ? "" : "s"}`, "You have jobs marked interesting that have not moved to applied.", "/jobs/pipeline", "high"));
  const resumeTasks = stageCount(model, "needs_custom_resume");
  if (resumeTasks > 0) actions.push(nextAction("resume", `Tailor resume for ${Math.min(2, resumeTasks)} strong-fit job${resumeTasks === 1 ? "" : "s"}`, "Resume tasks are blocking applications.", "/jobs/pipeline", "medium"));
  const copied = model.outreach.draftsCopied;
  if (copied > 0) actions.push(nextAction("send-dms", `Send ${copied} copied cold DM${copied === 1 ? "" : "s"} manually`, "Copied drafts are only useful once you send and track them.", "/applications/follow-ups", "medium"));
  if (model.summary.discoveryRuns === 0) actions.push(nextAction("daily-scout", "Run Daily Scout", "Fresh discovery keeps the top of the funnel moving.", "/discovery/control-center", "medium"));
  if (recommendedCount > model.summary.jobsReviewed) actions.push(nextAction("review", `Review ${Math.min(10, recommendedCount - model.summary.jobsReviewed)} unreviewed recommendation${recommendedCount - model.summary.jobsReviewed === 1 ? "" : "s"}`, "Recommendations need save/skip triage before they become useful.", "/discovery/control-center#review-queue", "medium"));
  const noisy = model.sourceAnalytics.ranking.noisiest;
  if (noisy && (noisy.noiseScore ?? 0) >= 50) actions.push(nextAction("source", `Clean up noisy ${noisy.displayName} source`, "This source is producing warnings, failures, or low-signal results.", "/discovery/control-center", "low"));
  return actions.slice(0, 8);
}

function filterByRange<T>(
  items: T[],
  range: JobSearchAnalyticsTimeRange,
  now: Date,
  dateSelector: (item: T) => string | null | undefined,
  warnings: string[],
  missingDateWarning: string,
) {
  if (range === "all") return items;
  let missingDate = false;
  const filtered = items.filter((item) => {
    const date = dateFromValue(dateSelector(item));
    if (!date) {
      missingDate = true;
      return false;
    }
    return inTimeRange(date, range, now);
  });
  if (missingDate) warnings.push(missingDateWarning);
  return filtered;
}

function inTimeRange(date: Date, range: JobSearchAnalyticsTimeRange, now: Date) {
  const value = date.getTime();
  if (range === "last_7") return value >= now.getTime() - 7 * 24 * 60 * 60 * 1000;
  if (range === "last_30") return value >= now.getTime() - 30 * 24 * 60 * 60 * 1000;
  if (range === "this_week") return value >= weekStart(now).getTime();
  if (range === "this_month") return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
  return true;
}

function getWeekBucket(map: Map<string, WeeklyTrendBucket>, date: Date) {
  const key = weekKey(date);
  const existing = map.get(key);
  if (existing) return existing;
  const created: WeeklyTrendBucket = {
    week: key,
    decisionsCreated: 0,
    decisionsUpdated: 0,
    jobsSaved: 0,
    jobsApplied: 0,
    coldDmDrafted: 0,
    dmsSentManually: 0,
    followUpsSent: 0,
    discoveryRuns: 0,
    dailyLoopsCompleted: 0,
  };
  map.set(key, created);
  return created;
}

function weekKey(date: Date) {
  const start = weekStart(date);
  return `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
}

function weekStart(date: Date) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const day = copy.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  copy.setDate(copy.getDate() + diff);
  return copy;
}

function decisionDate(decision: JobDecisionListItem) {
  return decision.updated_at ?? decision.last_status_changed_at ?? decision.created_at;
}

function recommendationDate(item: RecommendedJobMatch) {
  return item.scored_at ?? item.published_at;
}

function runDate(item: DiscoveryRunListItem) {
  return item.finished_at ?? item.started_at;
}

function followUpDate(item: ApplicationFollowUpItem) {
  return item.updated_at ?? item.last_action_at ?? item.sent_at ?? item.created_at;
}

function watchlistDate(item: CompanyWatchlistResponse) {
  return item.updated_at ?? item.last_reviewed_at ?? item.created_at;
}

function loopDate(item: DailyOperatingLoopState) {
  return item.completedAt ?? item.lastUpdatedAt ?? item.startedAt ?? item.date;
}

function metric(id: string, label: string, value: number, estimated = false): AnalyticsMetric {
  return { id, label, value, estimated };
}

function conversion(id: string, label: string, numerator: number, denominator: number): ConversionMetric {
  const value = denominator > 0 ? Math.round((numerator / denominator) * 100) : null;
  return { id, label, numerator, denominator, value, labelValue: value === null ? "Not enough data" : `${value}%` };
}

function labelRate(numerator: number, denominator: number) {
  return denominator > 0 ? `${Math.round((numerator / denominator) * 100)}%` : "Not enough data";
}

function statusOf(decision: JobDecisionListItem) {
  return decision.decision_status ?? decision.status ?? "saved";
}

function stageCount(model: JobSearchAnalyticsModel, stageId: string) {
  return model.funnel.find((stage) => stage.id === stageId)?.count ?? 0;
}

function nextAction(id: string, label: string, reason: string, href: string, priority: JobSearchNextAction["priority"]): JobSearchNextAction {
  return { id, label, reason, href, priority };
}

function bottleneck(id: string, severity: JobSearchBottleneck["severity"], title: string, reason: string, suggestedAction: string, href: string): JobSearchBottleneck {
  return { id, severity, title, reason, suggestedAction, href };
}

function uniqueCount(values: Array<string | null | undefined>) {
  return new Set(values.filter(Boolean)).size;
}

function unique<T>(values: T[]) {
  return Array.from(new Set(values));
}

function dateFromValue(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function latestDate(values: Array<string | null | undefined>) {
  const dates = values.map(dateFromValue).filter((date): date is Date => Boolean(date));
  return dates.sort((a, b) => b.getTime() - a.getTime())[0] ?? null;
}

function daysBetween(from: Date, to: Date) {
  return Math.floor((to.getTime() - from.getTime()) / (24 * 60 * 60 * 1000));
}

function maxBy<T>(items: T[], selector: (item: T) => number | null | undefined) {
  let best: T | null = null;
  let bestValue = 0;
  for (const item of items) {
    const value = selector(item) ?? 0;
    if (best === null || value > bestValue) {
      best = item;
      bestValue = value;
    }
  }
  return bestValue > 0 ? best : null;
}
